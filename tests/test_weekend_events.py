from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from growth_orchestrator.weekend_events import load_verified_weekend_events


def _write_events(config_root: Path, project: str, events: list[dict]) -> None:
    growth_dir = config_root / project / "growth"
    growth_dir.mkdir(parents=True, exist_ok=True)
    (growth_dir / "weekend_events.json").write_text(json.dumps(events), encoding="utf-8")


def test_load_verified_weekend_events_returns_approved_events_overlapping_weekend(tmp_path: Path) -> None:
    _write_events(
        tmp_path,
        "venho_hotel",
        [
            {
                "name": "Cho phien dem",
                "start_date": "2026-08-08",
                "end_date": "2026-08-09",
                "location": "Ho Tay",
                "description": "Cho dem cuoi tuan",
                "source_link": "https://example.com/event",
                "status": "approved",
            }
        ],
    )
    result = load_verified_weekend_events(
        "venho_hotel", config_root=tmp_path, today=date(2026, 8, 8)
    )
    assert len(result) == 1
    assert result[0]["name"] == "Cho phien dem"


def test_load_verified_weekend_events_skips_pending_approval(tmp_path: Path) -> None:
    _write_events(
        tmp_path,
        "venho_hotel",
        [
            {
                "name": "Chua duyet",
                "start_date": "2026-08-08",
                "end_date": "2026-08-09",
                "status": "pending_approval",
            }
        ],
    )
    result = load_verified_weekend_events(
        "venho_hotel", config_root=tmp_path, today=date(2026, 8, 8)
    )
    assert result == []


def test_load_verified_weekend_events_skips_events_outside_window(tmp_path: Path) -> None:
    _write_events(
        tmp_path,
        "venho_hotel",
        [
            {
                "name": "Su kien tuan sau",
                "start_date": "2026-08-15",
                "end_date": "2026-08-16",
                "status": "approved",
            }
        ],
    )
    result = load_verified_weekend_events(
        "venho_hotel", config_root=tmp_path, today=date(2026, 8, 8)
    )
    assert result == []


def test_load_verified_weekend_events_missing_file_returns_empty(tmp_path: Path) -> None:
    result = load_verified_weekend_events("venho_hotel", config_root=tmp_path, today=date(2026, 8, 8))
    assert result == []
