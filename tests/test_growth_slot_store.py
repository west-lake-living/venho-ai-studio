from __future__ import annotations

from pathlib import Path

import pytest

from growth_orchestrator.domain.publishing_slot import PublishingSlot
from shared.jobs.slot_store import SlotStore


def _slot(slot_id: str = "slot-2026-08-10-monday", slot_date: str = "2026-08-10") -> PublishingSlot:
    return PublishingSlot(slot_id=slot_id, slot_date=slot_date, slot_type="regular", lane="regular")


def test_ensure_slots_is_idempotent(tmp_path: Path) -> None:
    store = SlotStore(db_path=tmp_path / "growth.db")
    assert store.ensure_slots([_slot()]) == 1
    # re-inserting the same slot_id must not duplicate or reset an already-progressed slot
    assert store.ensure_slots([_slot()]) == 0
    assert store.get("slot-2026-08-10-monday").status == "OPEN"


def test_transition_persists_and_validates(tmp_path: Path) -> None:
    store = SlotStore(db_path=tmp_path / "growth.db")
    store.ensure_slots([_slot()])

    updated = store.transition("slot-2026-08-10-monday", "DRAFT_ASSIGNED")
    assert updated.status == "DRAFT_ASSIGNED"
    assert store.get("slot-2026-08-10-monday").status == "DRAFT_ASSIGNED"

    with pytest.raises(ValueError):
        store.transition("slot-2026-08-10-monday", "DISPATCHED")


def test_transition_unknown_slot_raises_keyerror(tmp_path: Path) -> None:
    store = SlotStore(db_path=tmp_path / "growth.db")
    with pytest.raises(KeyError):
        store.transition("nope", "DRAFT_ASSIGNED")


def test_transition_stores_content_package_id(tmp_path: Path) -> None:
    store = SlotStore(db_path=tmp_path / "growth.db")
    store.ensure_slots([_slot()])
    store.transition("slot-2026-08-10-monday", "DRAFT_ASSIGNED")
    updated = store.transition("slot-2026-08-10-monday", "PENDING_APPROVAL", content_package_id="pkg-1")
    assert updated.content_package_id == "pkg-1"
    assert store.get("slot-2026-08-10-monday").content_package_id == "pkg-1"


def test_list_for_week_filters_by_date(tmp_path: Path) -> None:
    store = SlotStore(db_path=tmp_path / "growth.db")
    store.ensure_slots(
        [
            _slot("slot-2026-08-10-monday", "2026-08-10"),
            _slot("slot-2026-08-12-wednesday", "2026-08-12"),
            _slot("slot-2026-08-17-monday", "2026-08-17"),  # next week
        ]
    )
    week = store.list_for_week(["2026-08-10", "2026-08-12"])
    assert {slot.slot_id for slot in week} == {"slot-2026-08-10-monday", "slot-2026-08-12-wednesday"}
