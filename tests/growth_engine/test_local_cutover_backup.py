from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path
import sqlite3

import pytest

from growth_engine.adapters.outbound.backup.restore import RestoreBackup
from growth_engine.adapters.outbound.backup.sqlite_backup import BackupError, SqliteBackup, _prune_staging, staged_backups
from growth_engine.adapters.inbound.cli.cutover_ops import fresh_backup
from growth_engine.settings import Settings


def test_local_backup_captures_wal_media_and_restores_only_the_copy(tmp_path):
    db = tmp_path / "growth.db"
    media = tmp_path / "media"
    media.mkdir()
    (media / "photo.jpg").write_bytes(b"original bytes")
    sha = hashlib.sha256(b"original bytes").hexdigest()
    with sqlite3.connect(db) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE media_assets (original_key, source_sha256)")
        conn.execute("CREATE TABLE media_variants (object_key, sha256)")
        conn.execute("""CREATE TABLE runtime_controls (
            environment PRIMARY KEY, publish_mode, global_pause, dispatch_epoch, row_version, updated_at
        )""")
        conn.execute("INSERT INTO runtime_controls VALUES ('production','LIVE_MANUAL',0,'old',1,0)")
        conn.execute("INSERT INTO media_assets VALUES (?,?)", ("photo.jpg", sha))
        conn.commit()
        result = SqliteBackup().stage(db_path=db, media_root=media, now_ms=1_800_000_000_000)
        assert result.destination.stat().st_mode & 0o777 == 0o600
        assert result.destination.parent.stat().st_mode & 0o777 == 0o700
        settings = Settings(env="production", db_path=str(db), media_root=str(media))
        from unittest.mock import patch
        with patch("growth_engine.adapters.inbound.cli.cutover_ops.now_ms", return_value=1_800_003_599_999):
            assert fresh_backup(settings) == result.destination
        with patch("growth_engine.adapters.inbound.cli.cutover_ops.now_ms", return_value=1_800_003_600_000):
            with pytest.raises(ValueError, match="one_hour_old"):
                fresh_backup(settings)
        restored = RestoreBackup().restore_archive(
            archive=result.destination, target=tmp_path / "restore", now_ms=1_800_000_000_001
        )
        with sqlite3.connect(restored.db_path) as restored_conn:
            assert restored_conn.execute("SELECT publish_mode,global_pause,dispatch_epoch FROM runtime_controls").fetchone()[:2] == ("DISABLED", 1)
        assert (restored.media_root / "photo.jpg").read_bytes() == b"original bytes"
        assert conn.execute("SELECT publish_mode,global_pause,dispatch_epoch FROM runtime_controls").fetchone() == ("LIVE_MANUAL", 0, "old")
        (media / "photo.jpg").unlink()
        with pytest.raises(BackupError, match="missing"):
            SqliteBackup().stage(db_path=db, media_root=media, now_ms=1_800_000_000_002)
        assert [path for _, path in staged_backups(result.destination.parent)] == [result.destination]


def test_local_backup_retains_newest_per_hour_day_week(tmp_path: Path):
    now = datetime(2026, 11, 24, 12, tzinfo=timezone.utc)
    for i in range(24 * 70):
        stamp = int((now - timedelta(hours=i)).timestamp() * 1000)
        (tmp_path / f"gc2-{stamp}.tar.gz").touch()
    _prune_staging(tmp_path)
    kept = [datetime.fromtimestamp(stamp / 1000, timezone.utc) for stamp, _ in staged_backups(tmp_path)]
    assert kept[:48] == [now - timedelta(hours=i) for i in range(48)]
    assert all((now - timedelta(days=i)).date() in {entry.date() for entry in kept} for i in range(14))
    assert len({entry.isocalendar()[:2] for entry in kept}) == 8


def test_legacy_inventory_blocks_future_sends_and_in_flight_rows():
    import runpy

    tool = Path(__file__).resolve().parents[2] / "ops/asus-server/growth-engine/legacy-cutover-snapshot.py"
    blockers = runpy.run_path(str(tool))["blockers"]
    registry = {"publications": [
        {"slot_id": "slot-2026-11-23-fb", "status": "PUBLISHED"},
        {"slot_id": "slot-2026-11-23-fb", "status": "DISPATCHING"},
        {"slot_id": "slot-2026-11-25-fb", "status": "APPROVED_SCHEDULED"},
        {"slot_id": "slot-2026-11-27-ig", "status": "PENDING_APPROVAL"},
        {"slot_id": "slot-2026-11-28-fb", "status": "CANCELLED"},
    ]}
    assert blockers(registry, "2026-11-25") == {
        "dispatching": 1, "approved_scheduled": 1, "pending_approval": 1,
    }


def test_legacy_snapshot_includes_insights_wal_and_checksum(tmp_path):
    import json
    import runpy

    tool = Path(__file__).resolve().parents[2] / "ops/asus-server/growth-engine/legacy-cutover-snapshot.py"
    snapshot = runpy.run_path(str(tool))["snapshot"]
    legacy = tmp_path / "legacy"
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    project = legacy / "data/projects/venho_hotel"
    (project / "publishing").mkdir(parents=True)
    (project / "growth").mkdir()
    (project / "publishing/publication_registry.json").write_text('{"publications":[]}')
    (project / "growth/slots_snapshot.json").write_text("{}")
    insights = tmp_path / "insights.db"
    with sqlite3.connect(project / "growth/growth.db") as growth:
        growth.execute("CREATE TABLE slots (id)")
    with sqlite3.connect(insights) as source:
        source.execute("PRAGMA journal_mode=WAL")
        source.execute("CREATE TABLE metrics (views)")
        source.execute("INSERT INTO metrics VALUES (42)")
        source.commit()
        assert snapshot(legacy, evidence, check=False, insights=insights)
        target = evidence / "legacy-snapshot"
        copied = target / "source/insights.db"
        manifest = json.loads((target / "manifest.json").read_text())
        assert len(manifest) == 4
        assert manifest["insights.db"] == hashlib.sha256(copied.read_bytes()).hexdigest()
        with sqlite3.connect(copied) as restored:
            assert restored.execute("SELECT views FROM metrics").fetchone() == (42,)
        assert snapshot(legacy, evidence, check=False, insights=insights)


def test_cutover_holds_os_timer_across_steps_and_restores_previous_state(tmp_path):
    import subprocess

    wrapper = Path(__file__).resolve().parents[2] / "ops/asus-server/growth-engine/cutover-window.sh"
    functions = wrapper.read_text().split("os_timer_active_state() {", 1)[1].split("legacy_clear() {", 1)[0]
    fake_systemctl = r'''
systemctl() {
  [[ "$1" == --user ]]
  case "$2" in
    show) if [[ "$3" == venho-os-deploy.service ]]; then echo inactive; else cat "$actual"; fi ;;
    stop) echo inactive > "$actual" ;;
    start) echo active > "$actual" ;;
    *) return 1 ;;
  esac
}
'''
    subprocess.run(
        ["bash", "-ec", fake_systemctl + "os_timer_active_state() {" + functions + r'''
os_timer=venho-os-deploy.timer
os_timer_state="$1/prior"
actual="$1/actual"
fail() { return 1; }
echo active > "$actual"
hold_os_timer
hold_os_timer
[[ "$(cat "$os_timer_state")" == active ]]
require_os_timer_held
restore_os_timer
[[ "$(cat "$actual")" == active ]]
''', "test", str(tmp_path)],
        check=True,
    )
