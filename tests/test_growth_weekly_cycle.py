from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from shutil import copyfile

import pytest

import growth_orchestrator.application.weekly_cycle as weekly_cycle_module
from growth_orchestrator.application.daily_cycle import DailyCycleResult
from growth_orchestrator.application.weekly_cycle import WEEKLY_CADENCE_ORDER, run_weekly_cycle
from shared.jobs.job_store import JobStore
from shared.jobs.slot_store import SlotStore


def test_publish_scheduler_is_independent_from_weekly_approval() -> None:
    workflow = Path(".github/workflows/growth-publish-scheduler.yml").read_text(encoding="utf-8")

    assert 'cron: "0 2 * * 1,3,5,6"' in workflow
    assert "args=(dispatch-due --allow-shadow)" in workflow
    assert "--allow-shadow" in workflow
    assert "--catch-up-today" in workflow
    assert "slots_snapshot.json" in workflow
    assert "approve-week" not in workflow
    assert "MAKE_GROWTH_WEBHOOK_URL" in workflow


def _tmp_data_root(tmp_path: Path) -> Path:
    root = tmp_path / "data" / "projects"
    knowledge_dir = root / "venho_hotel" / "knowledge"
    knowledge_dir.mkdir(parents=True)
    for name in ["VENHO_HOTEL_WESTLAKE_DNA.json", "VENHO_HOTEL_LAKE_VIEW_ROOM_DNA.json", "VENHO_HOTEL_OUTSIDE_DNA.json"]:
        copyfile(Path("data/projects/venho_hotel/knowledge") / name, knowledge_dir / name)
    return root


def test_run_weekly_cycle_one_day_crash_does_not_drop_the_other_days(tmp_path: Path, monkeypatch) -> None:
    """Regression test: before this fix, an uncaught exception on any single
    cadence day (e.g. a topic-config bug on Wednesday) aborted the entire
    weekly batch, dropping Friday/Saturday too."""
    data_root = _tmp_data_root(tmp_path)

    def _fake_run_daily_cycle(day: str, **kwargs):
        if day == "wednesday":
            raise ValueError("simulated topic config error")
        return DailyCycleResult(day=day, topic={"topic": "ok"}, publications=[{"platform": "facebook"}])

    monkeypatch.setattr(weekly_cycle_module, "run_daily_cycle", _fake_run_daily_cycle)

    with pytest.raises(RuntimeError, match="Weekly cycle incomplete"):
        run_weekly_cycle(data_root=data_root, start_date=date(2026, 8, 10))

    # The remaining cadence days still run, but the job is retryable instead
    # of silently becoming SUCCEEDED with an incomplete approval queue.
    job_store = JobStore(db_path=data_root / "venho_hotel" / "growth" / "growth.db")
    assert job_store.get("venho_hotel-weekly-v2-2026-W33")["status"] == "RETRYABLE_FAILED"


def test_run_weekly_cycle_fails_when_a_required_platform_is_missing(tmp_path: Path, monkeypatch) -> None:
    data_root = _tmp_data_root(tmp_path)

    def _fake_run_daily_cycle(day: str, **kwargs):
        return DailyCycleResult(day=day, topic={"topic": "ok"}, publications=[{"platform": "facebook"}])

    monkeypatch.setattr(weekly_cycle_module, "run_daily_cycle", _fake_run_daily_cycle)

    with pytest.raises(RuntimeError, match="missing required platforms instagram"):
        run_weekly_cycle(data_root=data_root, platforms=["facebook", "instagram"], start_date=date(2026, 8, 10))


def test_run_weekly_cycle_ensures_slots_for_the_week_before_running(tmp_path: Path, monkeypatch) -> None:
    data_root = _tmp_data_root(tmp_path)

    def _fake_run_daily_cycle(day: str, **kwargs):
        return DailyCycleResult(day=day, topic={"topic": "ok"}, publications=[{"platform": "facebook"}])

    monkeypatch.setattr(weekly_cycle_module, "run_daily_cycle", _fake_run_daily_cycle)

    monday = date(2026, 8, 10)
    run_weekly_cycle(data_root=data_root, start_date=monday)

    slot_store = SlotStore(db_path=data_root / "venho_hotel" / "growth" / "growth.db")
    assert slot_store.get("slot-2026-08-10-monday") is not None
    assert slot_store.get("slot-2026-08-12-wednesday") is not None
    assert slot_store.get("slot-2026-08-14-friday") is not None
    assert slot_store.get("slot-2026-08-15-saturday") is not None


def test_run_weekly_cycle_is_idempotent_per_iso_week(tmp_path: Path, monkeypatch) -> None:
    """A second call for the same ISO week (e.g. workflow manually
    re-triggered) must not regenerate/re-spend budget on a duplicate batch."""
    data_root = _tmp_data_root(tmp_path)
    call_count = {"n": 0}

    def _fake_run_daily_cycle(day: str, **kwargs):
        call_count["n"] += 1
        return DailyCycleResult(day=day, topic={"topic": "ok"}, publications=[{"platform": "facebook"}])

    monkeypatch.setattr(weekly_cycle_module, "run_daily_cycle", _fake_run_daily_cycle)

    monday = date(2026, 8, 10)
    first = run_weekly_cycle(data_root=data_root, start_date=monday)
    assert first.skipped_already_run is False
    assert call_count["n"] == len(WEEKLY_CADENCE_ORDER)

    second = run_weekly_cycle(data_root=data_root, start_date=monday)
    assert second.skipped_already_run is True
    assert second.days == []
    assert call_count["n"] == len(WEEKLY_CADENCE_ORDER)  # unchanged -- no re-run

    # A different ISO week is a fresh, unclaimed job and must run normally.
    next_monday = date(2026, 8, 17)
    third = run_weekly_cycle(data_root=data_root, start_date=next_monday)
    assert third.skipped_already_run is False
    assert call_count["n"] == 2 * len(WEEKLY_CADENCE_ORDER)


def test_run_weekly_cycle_recovers_a_week_stuck_running_from_a_crashed_prior_attempt(
    tmp_path: Path, monkeypatch
) -> None:
    """Regression test (Phase 5, stale-job recovery): before this fix, a
    previous real run that crashed/was cancelled mid-flight (never reaching
    job_store.complete()/fail()) left the week's job stuck RUNNING under an
    expired lease forever -- every future trigger for that ISO week would
    silently no-op (skipped_already_run=True) instead of ever retrying."""
    data_root = _tmp_data_root(tmp_path)

    def _fake_run_daily_cycle(day: str, **kwargs):
        return DailyCycleResult(day=day, topic={"topic": "ok"}, publications=[{"platform": "facebook"}])

    monkeypatch.setattr(weekly_cycle_module, "run_daily_cycle", _fake_run_daily_cycle)

    monday = date(2026, 8, 10)
    project = "venho_hotel"
    iso_year, iso_week, _ = monday.isocalendar()
    week_key = f"{project}-weekly-v2-{iso_year}-W{iso_week:02d}"

    growth_db = data_root / project / "growth" / "growth.db"
    job_store = JobStore(db_path=growth_db)
    job_store.enqueue(
        job_id=week_key, idempotency_key=week_key, job_type="weekly_cycle",
        version="2", scheduled_at=datetime.now().isoformat(), trace_id=week_key, payload={"project": project},
    )
    # Simulate a crashed prior attempt: claimed, never completed/failed, and
    # its lease is already in the past.
    job_store.claim(owner="stale-worker", lease_seconds=-100)
    assert job_store.get(week_key)["status"] == "RUNNING"

    result = run_weekly_cycle(data_root=data_root, start_date=monday)

    assert result.skipped_already_run is False
    assert len(result.days) == len(WEEKLY_CADENCE_ORDER)
    assert job_store.get(week_key)["status"] == "SUCCEEDED"
