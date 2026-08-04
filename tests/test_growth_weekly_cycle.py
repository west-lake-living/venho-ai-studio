from __future__ import annotations

from pathlib import Path
from shutil import copyfile

import growth_orchestrator.application.weekly_cycle as weekly_cycle_module
from growth_orchestrator.application.daily_cycle import DailyCycleResult
from growth_orchestrator.application.weekly_cycle import WEEKLY_CADENCE_ORDER, run_weekly_cycle


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
