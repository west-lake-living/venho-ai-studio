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


@pytest.mark.parametrize("present", [False, True])
def test_legacy_snapshot_insights_state_and_checksum(tmp_path, capsys, present):
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
    if present:
        with sqlite3.connect(insights) as source:
            source.execute("PRAGMA journal_mode=WAL")
            source.execute("CREATE TABLE metrics (views)")
            source.execute("INSERT INTO metrics VALUES (42)")
            source.commit()
            assert snapshot(legacy, evidence, check=False, insights=insights)
    else:
        assert snapshot(legacy, evidence, check=True, insights=insights)
        assert snapshot(legacy, evidence, check=False, insights=insights)
        assert "INSIGHTS=ABSENT (D2 deferred)" in capsys.readouterr().out

    target = evidence / "legacy-snapshot"
    copied = target / "source/insights.db"
    manifest = json.loads((target / "manifest.json").read_text())
    if present:
        assert manifest["insights.db"] == hashlib.sha256(copied.read_bytes()).hexdigest()
        with sqlite3.connect(copied) as restored:
            assert restored.execute("SELECT views FROM metrics").fetchone() == (42,)
    else:
        assert manifest["insights.db"] == {"status": "ABSENT", "reason": "t0_06_never_deployed"}
        assert not copied.exists()
        from growth_engine.adapters.outbound.legacy.importer import LegacyImportDryRun

        report = tmp_path / "dry-run.md"
        LegacyImportDryRun().run(target / "source", report)
        assert report.is_file()

    for check in (True, False):
        assert snapshot(legacy, evidence, check=check, insights=insights)

    if present:
        insights.unlink()
    else:
        insights.touch()
    for check in (True, False):
        with pytest.raises(ValueError, match="presence_changed_after_snapshot"):
            snapshot(legacy, evidence, check=check, insights=insights)


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


def test_t3_wrapper_runs_with_absent_insights(tmp_path):
    import os
    import shutil
    import subprocess
    import sys

    ops = Path(__file__).resolve().parents[2] / "ops/asus-server/growth-engine"
    root = tmp_path / "venho/growth-engine/current"
    deployed = root / "ops/asus-server/growth-engine"
    deployed.mkdir(parents=True)
    shutil.copy(ops / "legacy-cutover-snapshot.py", deployed)
    switch = deployed.parent / "venho-os/growth-backend-switch.sh"
    switch.parent.mkdir()
    switch.write_text('touch "$HOME/os-v2"\n')
    venv = root / ".venv/bin"
    venv.mkdir(parents=True)
    (venv / "python").symlink_to(sys.executable)
    (deployed / "setup-production-make-bearers.py").write_text("pass\n")
    project = tmp_path / "venho/growth-runtime/venho-ai-studio/data/projects/venho_hotel"
    (project / "publishing").mkdir(parents=True)
    (project / "growth").mkdir()
    (project / "publishing/publication_registry.json").write_text('{"publications":[]}')
    (project / "growth/slots_snapshot.json").write_text("{}")
    with sqlite3.connect(project / "growth/growth.db") as db:
        db.execute("CREATE TABLE slots (id)")
    engine = deployed / "run-with-legacy-provider-env.sh"
    engine.write_text('''#!/bin/bash
set -eu
if [[ "$1" == legacy-import ]]; then
  [[ "$2" == --dry-run && -f "$4/growth.db" && ! -e "$4/insights.db" ]]
  echo report > "$6"
fi
echo "$*" >> "$HOME/engine.calls"
''')
    engine.chmod(0o700)
    script = (ops / "cutover-window.sh").read_text()
    start = script.index("confirm() {")
    finish = script.index("control() {", start)
    # Use real snapshot checks and wrapper sequencing, with all host mutations stubbed.
    script = script[:start] + r'''
confirm() { :; }
date() { if [[ "$1" == +%F ]]; then echo 2026-11-24; else echo 1030; fi; }
flock() { :; }
curl() { if [[ -e "$HOME/os-v2" ]]; then echo 503; else echo 401; fi; }
git() { case "$3" in rev-parse|hash-object) echo matched ;; esac; }
gh() {
  if [[ "$1" == workflow ]]; then touch "$HOME/workflow-off"
  elif [[ "$2" == --paginate ]]; then printf '0\n0\n'
  elif [[ -e "$HOME/workflow-off" ]]; then echo disabled_manually
  else echo active; fi
}
systemctl() {
  case "$2" in
    show)
      case "$3" in
        venho-os-deploy.timer)
          if [[ -e "$HOME/os-timer-off" ]]; then echo inactive; else echo active; fi ;;
        *.service) echo inactive ;;
        *) if [[ -e "$HOME/timers-off" ]]; then
             if [[ "$4" == *UnitFileState* || "$5" == UnitFileState ]]; then echo disabled; else echo inactive; fi
           elif [[ "$5" == UnitFileState ]]; then echo enabled; else echo active; fi ;;
      esac ;;
    stop) touch "$HOME/os-timer-off" ;;
    disable) touch "$HOME/timers-off" ;;
    start) if [[ "$3" == venho-os-deploy.timer ]]; then rm "$HOME/os-timer-off"; fi ;;
    restart|is-active) : ;;
  esac
}
''' + script[finish:]
    for step in ("stop-legacy", "snapshot", "switch-and-epoch", "rotate", "dry-run", "live"):
        result = subprocess.run(
            ["bash", "-s", "--", step], input=script, text=True, capture_output=True,
            env={**os.environ, "HOME": str(tmp_path)},
        )
        assert result.returncode == 0, (step, result.stdout, result.stderr)
        if step != "stop-legacy":
            assert "INSIGHTS=ABSENT (D2 deferred)" in result.stdout
    assert "cutover-ops resume-hanoi" in (tmp_path / "engine.calls").read_text()
