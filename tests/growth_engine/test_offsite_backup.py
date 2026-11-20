import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from growth_engine.adapters.inbound.cli import cutover_ops
from growth_engine.adapters.outbound.backup import offsite
from growth_engine.bootstrap import DoctorService
from growth_engine.settings import Settings

ROOT = Path(__file__).resolve().parents[2]
NOW = 1_800_000_000_000
FOLDER = "private-folder"
OWNER = "a" * 32


class FakeDrive:
    def __init__(self, failure=None):
        self.failure = failure
        self.files = {}
        self.trashed = []

    def check_folder(self, folder):
        assert folder == FOLDER

    def upload(self, folder, source, name, props):
        if self.failure == "upload":
            raise RuntimeError("provider detail must never be included")
        md5, sha256, size = offsite._checksums(source)
        file_id = f"backup-{len(self.files)}"
        self.files[file_id] = {
            "id": file_id, "name": name, "parents": [folder], "trashed": False, "appProperties": props,
            "size": str(size), "md5Checksum": "0" * 32 if self.failure == "checksum" else md5,
            "sha256Checksum": "0" * 64 if self.failure == "sha256" else sha256,
        }
        return {"id": file_id}

    def get(self, file_id):
        return self.files[file_id]

    def mark_verified(self, file_id):
        self.files[file_id]["appProperties"]["gc2FileId"] = file_id

    def list(self, folder, owner):
        # Deliberately include unrelated rows to verify client-side validation.
        return list(self.files.values())

    def trash(self, file_id):
        self.trashed.append(file_id)
        self.files[file_id]["trashed"] = True


@pytest.fixture
def staged_db(tmp_path, monkeypatch):
    monkeypatch.setenv("GE_BACKUP_DRIVE_FOLDER_ID", FOLDER)
    db = tmp_path / "growth.db"
    db.touch()
    staging = offsite.staging_directory(db)
    staging.mkdir()
    (staging / f"gc2-{NOW}.tar.gz").write_bytes(b"archive")
    return db


def encrypt_fake(source, target, _recipient):
    target.write_bytes(b"encrypted " + source.read_bytes())


@pytest.mark.parametrize(
    ("failure", "code"),
    [("encrypt", "offsite_encryption_failed"), ("upload", "offsite_drive_upload_failed"),
     ("checksum", "offsite_drive_checksum_or_metadata_mismatch"),
     ("sha256", "offsite_drive_checksum_or_metadata_mismatch")],
)
def test_failed_upload_reports_sanitized_code_alerts_once_and_has_no_receipt(staged_db, failure, code):
    drive = FakeDrive(failure)
    alert = Mock()

    def encrypt(source, target, recipient):
        if failure == "encrypt":
            raise RuntimeError("sensitive age diagnostic")
        encrypt_fake(source, target, recipient)

    for _ in range(2):
        with pytest.raises(offsite.OffsiteError, match=f"^{code}$"):
            offsite.upload_latest(staged_db, ROOT, lambda: drive, encrypt=encrypt, clock=lambda: NOW, alert=alert)
    alert.assert_called_once()
    assert code in alert.call_args.args[0]
    state = staged_db.parent / "backup-offsite"
    assert not (state / "latest.json").exists()
    assert not list(state.glob(".encrypted-*"))

    drive.failure = None
    result = offsite.upload_latest(staged_db, ROOT, lambda: drive, encrypt=encrypt_fake,
                                  clock=lambda: NOW, alert=alert)
    assert result["checksum"] == "PASS"
    assert not (state / "failure.json").exists()


def test_receipt_and_doctor_strictly_younger_than_26_hours(staged_db, monkeypatch):
    drive = FakeDrive()
    result = offsite.upload_latest(staged_db, ROOT, lambda: drive, encrypt=encrypt_fake, clock=lambda: NOW)
    assert result["result"] == "PASS"
    _, checksum = offsite.load_recipient(ROOT)
    receipt_path = staged_db.parent / "backup-offsite" / "latest.json"
    assert receipt_path.stat().st_mode & 0o777 == 0o600
    assert json.loads(receipt_path.read_text())["sha256"] == result["sha256"]

    doctor = DoctorService(
        Settings(env="production", db_path=str(staged_db)), connect=Mock(), migration_runner=Mock(),
        sqlite_version_check=Mock(), sqlite_version_error=ValueError, repo_root=ROOT,
    )
    monkeypatch.setattr(offsite, "check_recipient", lambda _: None)
    for age, expected in ((-1, "WARN"), (0, "PASS"), (offsite.MAX_OFFSITE_AGE_MS - 1, "PASS"),
                          (offsite.MAX_OFFSITE_AGE_MS, "WARN"), (offsite.MAX_OFFSITE_AGE_MS + 1, "WARN")):
        monkeypatch.setattr("growth_engine.bootstrap.time.time_ns", lambda: (NOW + age) * 1_000_000)
        recipient, doctor_age = doctor._offsite_checks()
        assert recipient.status == "PASS"
        assert doctor_age.status == expected

    offsite.require_fresh_remote(staged_db, ROOT, lambda: NOW, lambda: drive)
    drive.files["backup-0"]["md5Checksum"] = "0" * 32
    with pytest.raises(offsite.OffsiteError, match="remote_checksum_or_metadata_mismatch"):
        offsite.require_fresh_remote(staged_db, ROOT, lambda: NOW, lambda: drive)
    monkeypatch.setenv("GE_BACKUP_DRIVE_FOLDER_ID", "different-folder")
    assert offsite.receipt_status(staged_db, checksum, NOW)[0] is None


def test_retention_trashes_only_tool_owned_verified_files_in_the_folder():
    drive = FakeDrive()
    now = datetime(2026, 11, 28, 9, tzinfo=timezone.utc)
    md5, sha = "c" * 32, "d" * 64

    def row(file_id, days):
        stamp = int((now - timedelta(days=days)).timestamp() * 1000)
        return {"id": file_id, "name": f"gc2-{stamp}.tar.gz.age", "parents": [FOLDER], "trashed": False,
                "size": "123", "appProperties": {**offsite._props(OWNER, sha, md5), "gc2FileId": file_id},
                "md5Checksum": md5, "sha256Checksum": sha}

    drive.files = {str(i): row(str(i), i) for i in range(70)}
    drive.files.update({
        "manual": {**row("manual", 69), "appProperties": {}},
        "other_app_install": {**row("other_app_install", 69), "appProperties": offsite._props("b" * 32, sha, md5)},
        "other_folder": {**row("other_folder", 69), "parents": ["elsewhere"]},
        "broken": {**row("broken", 69), "sha256Checksum": "0" * 64},
        "manual_copy": {**row("manual_copy", 69), "appProperties": row("69", 69)["appProperties"]},
        "foreign_name": {**row("foreign_name", 69), "name": "other.age"},
    })
    real_get = drive.get

    def moved_before_trash(file_id):
        return {**real_get(file_id), "parents": ["elsewhere"]} if file_id == "69" else real_get(file_id)

    drive.get = moved_before_trash
    pruned = offsite._retain(drive, FOLDER, OWNER, "0")
    assert pruned == len(drive.trashed) > 0
    assert all(str(i) not in drive.trashed for i in range(14))
    assert all(file_id.isdecimal() for file_id in drive.trashed)
    assert "69" not in drive.trashed
    kept = [now - timedelta(days=i) for i in range(69) if str(i) not in drive.trashed]
    assert len({dt.isocalendar()[:2] for dt in kept}) == 8


def test_resume_all_blocks_old_backup_and_resumes_only_after_remote_check(staged_db, monkeypatch):
    drive = FakeDrive()
    offsite.upload_latest(staged_db, ROOT, lambda: drive, encrypt=encrypt_fake, clock=lambda: NOW)
    settings = Settings(env="production", db_path=str(staged_db))
    controls = Mock()
    monkeypatch.setattr("growth_engine.bootstrap.build_container", lambda _: SimpleNamespace(operator_controls=controls))
    monkeypatch.setattr(cutover_ops, "fresh_backup", Mock())
    monkeypatch.setattr(cutover_ops, "pending_gate", lambda *_, **__: {"result": "PASS"})
    channels = [{"channel_key": key, "enabled": 1, "paused": 0} for key in cutover_ops.TARGETS]
    monkeypatch.setattr(cutover_ops, "state", lambda *args: {
        "controls": {"global_pause": 1, "publish_mode": "LIVE_MANUAL"}, "channels": channels,
    })
    monkeypatch.setattr(offsite.GoogleDrive, "from_env", lambda: drive)
    monkeypatch.setattr(offsite, "check_recipient", lambda _: None)
    monkeypatch.setattr(cutover_ops, "now_ms", lambda: NOW + offsite.MAX_OFFSITE_AGE_MS)
    assert cutover_ops.offsite_warning(settings).startswith("WARN:")
    with pytest.raises(ValueError, match="offsite_backup_at_least_26_hours_old"):
        cutover_ops.gate(settings, "resume-all", "2026-11-27", actor="test", correlation_id="test")
    controls.resume.assert_not_called()

    monkeypatch.setattr(cutover_ops, "now_ms", lambda: NOW + offsite.MAX_OFFSITE_AGE_MS - 1)
    cutover_ops.gate(settings, "resume-all", "2026-11-27", actor="test", correlation_id="test")
    controls.resume.assert_called_once()


@pytest.mark.skipif(not shutil.which("age"), reason="age CLI is unavailable")
def test_recipient_is_accepted_by_real_age_and_checksum_matches(tmp_path):
    recipient, checksum = offsite.load_recipient(ROOT)
    offsite.check_recipient(recipient)
    config = tmp_path / offsite.CONFIG
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({"recipient": recipient, "recipient_sha256": checksum[::-1]}))
    with pytest.raises(offsite.OffsiteError, match="offsite_recipient_config_invalid"):
        offsite.load_recipient(tmp_path)


def test_google_adapter_uses_resumable_chunks_and_never_changes_permissions(tmp_path):
    pytest.importorskip("googleapiclient.http")
    service = Mock()
    files = service.files.return_value
    request = files.create.return_value
    request.next_chunk.side_effect = [(Mock(), None), (None, {"id": "backup-id"})]
    source = tmp_path / "cipher"
    source.write_bytes(b"ciphertext")
    created = offsite.GoogleDrive(service).upload(FOLDER, source, "backup.age", {"marker": "fake"})
    assert created == {"id": "backup-id"}
    kwargs = files.create.call_args.kwargs
    assert kwargs["media_body"].resumable()
    assert kwargs["body"]["parents"] == [FOLDER]
    assert request.next_chunk.call_count == 2
    service.permissions.assert_not_called()


@pytest.mark.skipif(not shutil.which("age") or not shutil.which("age-keygen"), reason="age CLI is unavailable")
def test_age_round_trip_restores_sqlite_and_manifest_from_drive_bytes(tmp_path, monkeypatch):
    import hashlib
    import sqlite3
    import subprocess

    from growth_engine.adapters.outbound.backup.restore import RestoreBackup
    from growth_engine.adapters.outbound.backup.sqlite_backup import SqliteBackup

    monkeypatch.setenv("GE_BACKUP_DRIVE_FOLDER_ID", FOLDER)
    identity = tmp_path / "test-identity"
    subprocess.run(["age-keygen", "-o", str(identity)], check=True, capture_output=True)
    recipient = subprocess.check_output(["age-keygen", "-y", str(identity)], text=True).strip()
    config = tmp_path / offsite.CONFIG
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({
        "recipient": recipient, "recipient_sha256": hashlib.sha256(recipient.encode()).hexdigest(),
    }))
    db = tmp_path / "growth.db"
    media = tmp_path / "media"
    media.mkdir()
    (media / "photo.jpg").write_bytes(b"original photo")
    with sqlite3.connect(db) as connection:
        connection.execute("CREATE TABLE media_assets (original_key, source_sha256)")
        connection.execute("CREATE TABLE media_variants (object_key, sha256)")
        connection.execute("INSERT INTO media_assets VALUES (?, ?)",
                           ("photo.jpg", hashlib.sha256(b"original photo").hexdigest()))
        connection.execute("""CREATE TABLE runtime_controls (
            environment PRIMARY KEY, publish_mode, global_pause, dispatch_epoch, row_version, updated_at
        )""")
        connection.execute("INSERT INTO runtime_controls VALUES ('production','LIVE_MANUAL',0,'old',1,0)")
    SqliteBackup().stage(db_path=db, media_root=media, now_ms=NOW)

    class DownloadableDrive(FakeDrive):
        def upload(self, folder, source, name, props):
            archived.write_bytes(source.read_bytes())
            return super().upload(folder, source, name, props)

    archived = tmp_path / "downloaded.age"
    drive = DownloadableDrive()
    proof = offsite.upload_latest(db, tmp_path, lambda: drive, clock=lambda: NOW)
    assert proof["sha256"] == hashlib.sha256(archived.read_bytes()).hexdigest()
    restored = RestoreBackup().restore(encrypted_backup=archived, target=tmp_path / "restored",
                                       identity_file=identity, now_ms=NOW)
    assert restored.dispatch_epochs_rotated == 1
    assert (restored.media_root / "photo.jpg").read_bytes() == b"original photo"
