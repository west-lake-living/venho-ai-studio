from __future__ import annotations

import json
import shutil
import sqlite3
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import uuid4

from growth_engine.adapters.outbound.backup.sqlite_backup import (
    AgeCrypto,
    AgeSubprocess,
    BackupError,
    _referenced_artifacts,
    _safe_key,
    _sha256,
)


@dataclass(frozen=True)
class RestoreResult:
    db_path: Path
    media_root: Path
    dispatch_epochs_rotated: int


class RestoreBackup:
    def __init__(self, crypto: AgeCrypto | None = None) -> None:
        self._crypto = crypto or AgeSubprocess()

    def restore(
        self,
        *,
        encrypted_backup: Path,
        target: Path,
        identity_file: Path,
        now_ms: int,
    ) -> RestoreResult:
        encrypted_backup = Path(encrypted_backup)
        target = Path(target)
        identity_file = Path(identity_file)
        if not encrypted_backup.is_file() or not identity_file.is_file():
            raise BackupError("backup archive or age identity is unavailable")
        if target.exists():
            raise BackupError("restore target must not already exist")

        with tempfile.TemporaryDirectory(prefix="gc2-restore-") as temporary:
            work = Path(temporary)
            archive = work / "backup.tar.gz"
            self._crypto.decrypt(encrypted_backup, archive, identity_file)
            extracted = work / "extracted"
            extracted.mkdir()
            _extract_safe(archive, extracted)
            manifest = _read_manifest(extracted / "manifest.json")
            db_snapshot = extracted / str(manifest.get("database", ""))
            if not db_snapshot.is_file():
                raise BackupError("backup database is missing")
            artifacts = manifest.get("artifacts")
            if not isinstance(artifacts, list):
                raise BackupError("backup artifact manifest is invalid")
            expected = {(str(row.get("object_key")), str(row.get("sha256"))) for row in artifacts if isinstance(row, dict)}
            referenced = set(_referenced_artifacts(db_snapshot))
            if expected != referenced:
                raise BackupError("backup artifact manifest does not match database references")
            staged_media = extracted / "media"
            for object_key, expected_sha in expected:
                media_file = staged_media / _safe_key(object_key)
                if not media_file.is_file() or _sha256(media_file) != expected_sha:
                    raise BackupError("backup is missing a referenced media artifact or its hash is invalid")
            _check_database(db_snapshot)
            target.mkdir(parents=True, exist_ok=False)
            db_path = target / "growth_engine.db"
            media_root = target / "media"
            try:
                shutil.copy2(db_snapshot, db_path)
                shutil.copytree(staged_media, media_root)
                rotated = _disable_and_rotate_epoch(db_path, now_ms)
                _check_database(db_path)
            except Exception:
                shutil.rmtree(target, ignore_errors=True)
                raise
            return RestoreResult(db_path, media_root, rotated)


def _extract_safe(archive: Path, destination: Path) -> None:
    try:
        with tarfile.open(archive, "r:gz") as tar:
            members = tar.getmembers()
            for member in members:
                name = PurePosixPath(member.name)
                if name.is_absolute() or any(part in {"", ".", ".."} for part in name.parts):
                    raise BackupError("archive contains an unsafe path")
                if not (member.isfile() or member.isdir()):
                    raise BackupError("archive contains an unsupported entry type")
            for member in members:
                name = PurePosixPath(member.name)
                target = destination.joinpath(*name.parts)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    source = tar.extractfile(member)
                    if source is None:
                        raise BackupError("archive file entry is unreadable")
                    with source, target.open("wb") as output:
                        shutil.copyfileobj(source, output)
    except (OSError, tarfile.TarError) as error:
        raise BackupError("backup archive is invalid") from None


def _read_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise BackupError("backup manifest is unreadable") from None
    if not isinstance(value, dict) or value.get("database") != "growth_engine.db":
        raise BackupError("backup manifest is invalid")
    return value


def _check_database(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()
        foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
        if integrity is None or integrity[0] != "ok" or foreign_keys:
            raise BackupError("restored database failed integrity checks")
    except sqlite3.Error as error:
        raise BackupError("restored database is unreadable") from None
    finally:
        connection.close()


def _disable_and_rotate_epoch(db_path: Path, now_ms: int) -> int:
    connection = sqlite3.connect(db_path, isolation_level=None)
    try:
        connection.execute("BEGIN IMMEDIATE")
        rows = connection.execute("SELECT environment FROM runtime_controls").fetchall()
        for (environment,) in rows:
            connection.execute(
                "UPDATE runtime_controls SET publish_mode='DISABLED', dispatch_epoch=?, global_pause=1, "
                "row_version=row_version+1, updated_at=? WHERE environment=?",
                (str(uuid4()), now_ms, environment),
            )
        connection.commit()
        return len(rows)
    except sqlite3.Error as error:
        if connection.in_transaction:
            connection.rollback()
        raise BackupError("restore could not disable publishing and rotate epoch") from None
    finally:
        connection.close()
