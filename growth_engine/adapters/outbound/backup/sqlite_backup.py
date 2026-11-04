from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass
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
                if not source.is_file():
                    raise BackupError(f"referenced media artifact is missing: {key}")
                actual_sha = _sha256(source)
                if actual_sha != expected_sha:
                    raise BackupError(f"referenced media artifact hash mismatch: {key}")
                target = bundle_root / "media" / key
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
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
            encrypted_temp = destination.with_name(f".{destination.name}.tmp")
            try:
                self._crypto.encrypt(archive, encrypted_temp, age_recipient)
                os.chmod(encrypted_temp, 0o600)
                os.link(encrypted_temp, destination)
                encrypted_temp.unlink()
            except Exception:
                encrypted_temp.unlink(missing_ok=True)
                destination.unlink(missing_ok=True)
                raise
            return BackupResult(destination, len(artifacts), now_ms)

    @staticmethod
    def _snapshot_database(source_path: Path, target_path: Path) -> None:
        source = sqlite3.connect(source_path)
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
