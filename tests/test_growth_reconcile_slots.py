from __future__ import annotations

from datetime import date
from pathlib import Path

from controlled_rollout.collect_real_scorecard_metrics import collect_real_scorecard_metrics
from growth_orchestrator.application.reconcile_slots import reconcile_slots
from growth_orchestrator.domain.publishing_slot import PublishingSlot
from publishing_gateway.publication_registry import PublicationRegistry
from shared.jobs.slot_store import SlotStore

_TODAY = date(2026, 10, 22)


def _setup(tmp_path: Path, slots: dict[str, tuple[str, list[str]]]) -> SlotStore:
    store = SlotStore(db_path=tmp_path / "venho_hotel" / "growth" / "growth.db")
    store.ensure_slots(
        PublishingSlot(slot_id=f"slot-{d}", slot_date=d, slot_type="regular", lane="regular", status=status)
        for d, (status, _) in slots.items()
    )
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    for d, (_, row_statuses) in slots.items():
        for i, status in enumerate(row_statuses):
            pid = f"pub-{d}-{i}"
            registry.reserve({"publication_id": pid, "content_package_id": pid, "idempotency_key": pid, "platform": "facebook"})
            registry.update(pid, status=status, slot_id=f"slot-{d}")
    return store


def test_past_slots_close_from_the_registry(tmp_path: Path) -> None:
    store = _setup(tmp_path, {
        "2026-08-14": ("MISSED", ["CANCELLED", "PUBLISHED"]),  # a post went out after all
        "2026-09-11": ("PENDING_APPROVAL", ["FAILED"]),
        "2026-10-21": ("PENDING_APPROVAL", ["CANCELLED", "CANCELLED"]),  # Harry cancelled the day
        "2026-10-19": ("DISPATCHED", ["GATEWAY_ACCEPTED"]),
        "2026-10-23": ("PENDING_APPROVAL", ["PENDING_APPROVAL"]),  # not past yet
    })

    changes = {c["slot_id"]: c for c in reconcile_slots(data_root=tmp_path, today=_TODAY)}

    assert changes["slot-2026-08-14"]["to"] == "COMPLETED"
    assert changes["slot-2026-09-11"] == {"slot_id": "slot-2026-09-11", "from": "PENDING_APPROVAL", "to": "MISSED", "reason": "no_publication:FAILED"}
    assert changes["slot-2026-10-21"]["reason"] == "all_cancelled"
    assert changes["slot-2026-10-19"]["to"] == "COMPLETED"
    assert "slot-2026-10-23" not in changes
    assert store.get("slot-2026-10-23").status == "PENDING_APPROVAL"
    assert reconcile_slots(data_root=tmp_path, today=_TODAY) == []  # idempotent


def test_empty_days_count_recent_unplanned_gaps_only(tmp_path: Path) -> None:
    _setup(tmp_path, {
        "2026-08-20": ("PENDING_APPROVAL", ["FAILED"]),  # outside the 28-day window
        "2026-10-07": ("PENDING_APPROVAL", ["FAILED", "REJECTED"]),
        "2026-10-21": ("PENDING_APPROVAL", ["CANCELLED"]),
    })
    reconcile_slots(data_root=tmp_path, today=_TODAY)

    metrics = collect_real_scorecard_metrics(data_root=tmp_path, version="t", today=_TODAY)["metrics"]

    assert metrics["unplanned_empty_days"] == 1  # only 07/10


def test_old_database_gains_the_reason_column(tmp_path: Path) -> None:
    import sqlite3

    db_path = tmp_path / "growth.db"
    with sqlite3.connect(db_path) as db:
        db.execute("CREATE TABLE publishing_slots (slot_id TEXT PRIMARY KEY, slot_date TEXT NOT NULL, slot_type TEXT NOT NULL, lane TEXT NOT NULL, status TEXT NOT NULL, content_package_id TEXT, filled_from TEXT, updated_at TEXT NOT NULL)")
    SlotStore(db_path=db_path)
    with sqlite3.connect(db_path) as db:
        assert "closed_reason" in {row[1] for row in db.execute("PRAGMA table_info(publishing_slots)")}
