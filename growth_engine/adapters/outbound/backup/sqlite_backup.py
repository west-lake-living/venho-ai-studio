from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Protocol


class BackupError(RuntimeError):
    pass


class AgeCrypto(Protocol):
    def encrypt(self, source: Path, destination: Path, recipient: str) -> None: ...
    def decrypt(self, source: Path, destination: Path, identity_file: Path) -> None: ...


class AgeSubprocess:
    def encrypt(self, source: Path, destination: Path, recipient: str) -> None:
        self._run(["age", "-r", recipient, "-o", str(destination), str(source)])

    def decrypt(self, source: Path, destination: Path, identity_file: Path) -> None:
        self._run(["age", "-d", "-i", str(identity_file), "-o", str(destination), str(source)])

    @staticmethod
    def _run(command: list[str]) -> None:
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except (OSError, subprocess.CalledProcessError) as error:
            raise BackupError(f"age command failed ({type(error).__name__})") from None


@dataclass(frozen=True)
class BackupResult:
    destination: Path
    artifact_count: int
    snapshot_at_ms: int


class SqliteBackup:
    def __init__(self, crypto: AgeCrypto | None = None) -> None:
        self._crypto = crypto or AgeSubprocess()

    def create(
        self,
        *,
        db_path: Path,
        media_root: Path,
        destination: Path,
        age_recipient: str,
        now_ms: int,
    ) -> BackupResult:
        if not age_recipient.strip() or "REQUIRED_FROM_P0" in age_recipient:
            raise BackupError("GE_AGE_RECIPIENT must be configured")
        return self._create(db_path, media_root, destination, now_ms, age_recipient)

    def stage(self, *, db_path: Path, media_root: Path, now_ms: int) -> BackupResult:
        directory = staging_directory(db_path)
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if directory.is_symlink() or directory.stat().st_uid != os.getuid():
            raise BackupError("invalid backup staging directory")
        directory.chmod(0o700)
        descriptor = os.open(directory / ".lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "rb") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            result = self._create(
                db_path, media_root, directory / f"gc2-{now_ms:013d}.tar.gz", now_ms, None
            )
            _prune_staging(directory)
            return result

    def _create(
        self, db_path: Path, media_root: Path, destination: Path, now_ms: int,
        age_recipient: str | None,
    ) -> BackupResult:
        db_path = Path(db_path)
        media_root = Path(media_root)
        destination = Path(destination)
        if not db_path.is_file() or not media_root.is_dir():
            raise BackupError("database or media root is unavailable")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise BackupError("backup destination already exists")

        with tempfile.TemporaryDirectory(prefix="gc2-backup-") as temporary:
            work = Path(temporary)
            snapshot_path = work / "growth_engine.db"
            self._snapshot_database(db_path, snapshot_path)
            artifact_rows = _referenced_artifacts(snapshot_path)
            bundle_root = work / "bundle"
            (bundle_root / "media").mkdir(parents=True)
            artifacts: list[dict[str, str]] = []
            for object_key, expected_sha in artifact_rows:
                key = _safe_key(object_key)
                source = media_root / key
                if not source.is_file() or not source.resolve().is_relative_to(media_root.resolve()):
                    raise BackupError(f"referenced media artifact is missing: {key}")
                target = bundle_root / "media" / key
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                actual_sha = _sha256(target)
                if actual_sha != expected_sha:
                    raise BackupError(f"referenced media artifact hash mismatch: {key}")
                artifacts.append({"object_key": key, "sha256": actual_sha})
            shutil.copy2(snapshot_path, bundle_root / "growth_engine.db")
            manifest = {
                "_synthetic": False,
                "snapshot_at_ms": now_ms,
                "database": "growth_engine.db",
                "artifacts": sorted(artifacts, key=lambda row: row["object_key"]),
            }
            (bundle_root / "manifest.json").write_text(
                json.dumps(manifest, sort_keys=True, separators=(",", ":")), encoding="utf-8"
            )
            archive = work / "backup.tar.gz"
            with tarfile.open(archive, "w:gz") as tar:
                tar.add(bundle_root / "growth_engine.db", arcname="growth_engine.db")
                tar.add(bundle_root / "manifest.json", arcname="manifest.json")
                tar.add(bundle_root / "media", arcname="media")
            # Publish only complete archives. The temporary file is on the same filesystem.
            with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".gc2-", delete=False) as temp:
                staged = Path(temp.name)
            try:
                if age_recipient is None:
                    shutil.copyfile(archive, staged)
                else:
                    staged.unlink()
                    self._crypto.encrypt(archive, staged, age_recipient)
                staged.chmod(0o600)
                with staged.open("rb") as output:
                    os.fsync(output.fileno())
                os.link(staged, destination)
            finally:
                staged.unlink(missing_ok=True)
            return BackupResult(destination, len(artifacts), now_ms)

    @staticmethod
    def _snapshot_database(source_path: Path, target_path: Path) -> None:
        source = sqlite3.connect(source_path.resolve().as_uri() + "?mode=ro", uri=True)
        target = sqlite3.connect(target_path)
        try:
            source.backup(target)
            integrity = target.execute("PRAGMA integrity_check").fetchone()
            foreign_keys = target.execute("PRAGMA foreign_key_check").fetchall()
            if integrity is None or integrity[0] != "ok" or foreign_keys:
                raise BackupError("SQLite snapshot failed integrity checks")
        except sqlite3.Error as error:
            raise BackupError("SQLite online backup failed") from None
        finally:
            target.close()
            source.close()


def staging_directory(db_path: Path) -> Path:
    return Path(db_path).parent / "backup-staging"


def staged_backups(directory: Path) -> list[tuple[int, Path]]:
    entries = []
    for path in directory.glob("gc2-*.tar.gz"):
        stamp = path.name.removeprefix("gc2-").removesuffix(".tar.gz")
        if len(stamp) == 13 and stamp.isascii() and stamp.isdecimal() and path.is_file() and not path.is_symlink():
            entries.append((int(stamp), path))
    return sorted(entries, reverse=True)


def _prune_staging(directory: Path) -> None:
    backups = staged_backups(directory)
    keep = set()
    for limit, bucket in (
        (48, lambda instant: (instant.date(), instant.hour)),
        (14, lambda instant: instant.date()),
        (8, lambda instant: instant.isocalendar()[:2]),
    ):
        seen = set()
        for stamp, path in backups:
            key = bucket(datetime.fromtimestamp(stamp / 1000, timezone.utc))
            if key not in seen:
                seen.add(key)
                keep.add(path)
                if len(seen) == limit:
                    break
    for _, path in backups:
        if path not in keep:
            path.unlink()


def _referenced_artifacts(db_path: Path) -> list[tuple[str, str]]:
    connection = sqlite3.connect(db_path)
    try:
        rows = connection.execute(
            """SELECT object_key, sha256 FROM media_variants
               UNION SELECT original_key, source_sha256 FROM media_assets
               WHERE original_key IS NOT NULL"""
        ).fetchall()
    except sqlite3.Error as error:
        raise BackupError("media artifact manifest query failed") from None
    finally:
        connection.close()
    result = [(str(key), str(sha)) for key, sha in rows]
    for _key, sha in result:
        if len(sha) != 64 or any(character not in "0123456789abcdef" for character in sha):
            raise BackupError("database contains an invalid artifact SHA-256")
    return result


def _safe_key(key: str) -> str:
    if not key or "\\" in key or "\x00" in key:
        raise BackupError("invalid media object key")
    path = PurePosixPath(key)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise BackupError("invalid media object key")
    return str(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
