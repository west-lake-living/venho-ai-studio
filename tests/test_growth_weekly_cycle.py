from __future__ import annotations

from datetime import date
from pathlib import Path
from shutil import copyfile

import growth_orchestrator.application.weekly_cycle as weekly_cycle_module
from growth_orchestrator.application.daily_cycle import DailyCycleResult
from growth_orchestrator.application.weekly_cycle import WEEKLY_CADENCE_ORDER, run_weekly_cycle
from shared.jobs.slot_store import SlotStore


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

    result = run_weekly_cycle(data_root=data_root)

    assert [day.day for day in result.days] == WEEKLY_CADENCE_ORDER
    wednesday = next(day for day in result.days if day.day == "wednesday")
    assert wednesday.publications == []
    assert wednesday.errors == [{"platform": "*", "error": "ValueError: simulated topic config error"}]
    other_days = [day for day in result.days if day.day != "wednesday"]
    assert all(day.publications for day in other_days)


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
