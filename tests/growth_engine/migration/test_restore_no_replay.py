from __future__ import annotations

import base64
import hashlib
import shutil
import sqlite3
import threading
from pathlib import Path

import pytest

from growth_engine.adapters.outbound.backup.restore import RestoreBackup
from growth_engine.adapters.outbound.backup.sqlite_backup import BackupError, SqliteBackup
from growth_engine.adapters.outbound.persistence.sqlite.migrator import MigrationRunner
from growth_engine.application.publishing.enqueue_due import EnqueueCommandClaims
from growth_engine.adapters.outbound.security.capability_tokens import CapabilityTokenManager, parse_key_ring


MIGRATIONS = Path(__file__).parents[3] / "growth_engine/adapters/outbound/persistence/sqlite/migrations"


class CopyAge:
    def encrypt(self, source: Path, destination: Path, recipient: str) -> None:
        assert recipient == "synthetic-age-recipient"
        shutil.copyfile(source, destination)

    def decrypt(self, source: Path, destination: Path, identity_file: Path) -> None:
        assert identity_file.read_text(encoding="utf-8") == "synthetic age identity"
        shutil.copyfile(source, destination)


def _database(path: Path, media_root: Path) -> tuple[str, str, bytes]:
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys=ON")
    MigrationRunner(MIGRATIONS).apply(connection, application_version="synthetic-test")
    now_ms = 1_800_000_000_000
    connection.execute(
        "INSERT INTO runtime_controls(environment,publish_mode,dispatch_epoch,global_pause,policy_version,updated_at) "
        "VALUES('production','LIVE_MANUAL','synthetic-old-epoch',0,'synthetic',?)",
        (now_ms,),
    )
    media = "_synthetic: true; note: cần thay bằng fixture thật từ P0-T03/P0-T04".encode("utf-8")
    media_sha = hashlib.sha256(media).hexdigest()
    original_key = f"originals/{media_sha[:2]}/{media_sha}"
    variant_key = f"variants/{media_sha[:2]}/{media_sha}.jpg"
    (media_root / original_key).parent.mkdir(parents=True)
    (media_root / original_key).write_bytes(media)
    (media_root / variant_key).parent.mkdir(parents=True)
    (media_root / variant_key).write_bytes(media)
    connection.execute(
        "INSERT INTO media_assets VALUES(?,?,?,?,?,?,?,?)",
        ("synthetic-asset", "upload", "synthetic-source", "synthetic-revision", media_sha, original_key,
         '{"_synthetic":true,"note":"cần thay bằng fixture thật từ P0-T03/P0-T04"}', now_ms),
    )
    connection.execute(
        "INSERT INTO media_variants VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        ("synthetic-variant", "synthetic-asset", "synthetic-transform", media_sha, variant_key,
         10, 10, "image/jpeg", len(media), "PASS", now_ms),
    )
    connection.execute("CREATE TABLE IF NOT EXISTS synthetic_pair(left_value INTEGER,right_value INTEGER)")
    connection.execute("INSERT INTO synthetic_pair VALUES(0,0)")
    connection.commit()
    connection.close()
    return original_key, variant_key, media


def test_online_backup_is_consistent_while_database_is_being_written(tmp_path: Path) -> None:
    db_path = tmp_path / "live.db"
    media_root = tmp_path / "media"
    media_root.mkdir()
    _database(db_path, media_root)
    backup_started = threading.Event()
    writer_finished = threading.Event()
    write_errors: list[BaseException] = []

    def writer() -> None:
        try:
            backup_started.wait(timeout=5)
            connection = sqlite3.connect(db_path, timeout=5)
            for value in range(1, 200):
                connection.execute("BEGIN IMMEDIATE")
                connection.execute("UPDATE synthetic_pair SET left_value=?, right_value=?", (value, value))
                connection.commit()
            connection.close()
        except BaseException as error:
            write_errors.append(error)
        finally:
            writer_finished.set()

    thread = threading.Thread(target=writer)
    thread.start()
    age = CopyAge()
    backup = SqliteBackup(age)
    original_snapshot = backup._snapshot_database

    def start_writer_then_snapshot(source: Path, target: Path) -> None:
        backup_started.set()
        original_snapshot(source, target)

    backup._snapshot_database = start_writer_then_snapshot
    result = backup.create(
        db_path=db_path,
        media_root=media_root,
        destination=tmp_path / "concurrent.age",
        age_recipient="synthetic-age-recipient",
        now_ms=1_800_000_000_000,
    )
    writer_finished.wait(timeout=5)
    thread.join(timeout=5)
    assert not write_errors
    assert result.artifact_count == 2

    import tarfile

    with tarfile.open(result.destination, "r:gz") as archive:
        snapshot = tmp_path / "snapshot.db"
        snapshot.write_bytes(archive.extractfile("growth_engine.db").read())
    connection = sqlite3.connect(snapshot)
    pair = connection.execute("SELECT left_value,right_value FROM synthetic_pair").fetchone()
    connection.close()
    assert pair[0] == pair[1]


def test_backup_fails_when_a_referenced_media_artifact_is_missing(tmp_path: Path) -> None:
    db_path = tmp_path / "live.db"
    media_root = tmp_path / "media"
    media_root.mkdir()
    original_key, _variant_key, _media = _database(db_path, media_root)
    (media_root / original_key).unlink()

    with pytest.raises(BackupError, match="missing"):
        SqliteBackup(CopyAge()).create(
            db_path=db_path,
            media_root=media_root,
            destination=tmp_path / "missing.age",
            age_recipient="synthetic-age-recipient",
            now_ms=1_800_000_000_000,
        )
    assert not (tmp_path / "missing.age").exists()


def test_restore_disables_publish_and_rotates_old_command_epoch(tmp_path: Path) -> None:
    db_path = tmp_path / "live.db"
    media_root = tmp_path / "media"
    media_root.mkdir()
    _original_key, variant_key, media = _database(db_path, media_root)
    key = base64.urlsafe_b64encode(bytes(range(32))).decode("ascii").rstrip("=")
    tokens = CapabilityTokenManager(parse_key_ring(f"synthetic-key:{key}"))
    old_token = tokens.issue(
        EnqueueCommandClaims(
            command_id="synthetic-command",
            delivery_id="synthetic-delivery",
            revision_id="synthetic-revision",
            channel_id="synthetic-channel",
            remote_account_id="synthetic-page",
            payload_hash="a" * 64,
            dispatch_epoch="synthetic-old-epoch",
            audience="make-route:synthetic-channel",
            expires_at_ms=1_900_000_000_000,
        )
    )
    archive = tmp_path / "backup.age"
    SqliteBackup(CopyAge()).create(
        db_path=db_path,
        media_root=media_root,
        destination=archive,
        age_recipient="synthetic-age-recipient",
        now_ms=1_800_000_000_000,
    )
    identity = tmp_path / "identity.txt"
    identity.write_text("synthetic age identity", encoding="utf-8")

    result = RestoreBackup(CopyAge()).restore(
        encrypted_backup=archive,
        target=tmp_path / "restored",
        identity_file=identity,
        now_ms=1_800_000_100_000,
    )

    connection = sqlite3.connect(result.db_path)
    mode, new_epoch, paused = connection.execute(
        "SELECT publish_mode,dispatch_epoch,global_pause FROM runtime_controls WHERE environment='production'"
    ).fetchone()
    connection.close()
    claims = tokens.verify(old_token, audience="make-route:synthetic-channel", now_ms=1_800_000_100_000)
    assert mode == "DISABLED"
    assert paused == 1
    assert result.dispatch_epochs_rotated == 1
    assert claims.dispatch_epoch != new_epoch
    assert (result.media_root / variant_key).read_bytes() == media
