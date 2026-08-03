from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from growth_orchestrator.domain.publishing_slot import PublishingSlot

_WEEKDAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def generate_slots(cadence_policy: dict[str, Any], *, start_date: date, horizon_days: int | None = None) -> list[PublishingSlot]:
    """Create OPEN PublishingSlot rows for every cadence day inside the horizon.

    Idempotent by construction: slot_id is deterministic from (date, day-name),
    so re-running this for an overlapping horizon yields identical slot_ids
    and the caller can INSERT OR IGNORE against the store.
    """
    horizon = horizon_days if horizon_days is not None else cadence_policy["slot_creation_horizon_days"]
    by_day = {entry["day"]: entry for entry in cadence_policy["slots"]}
    slots: list[PublishingSlot] = []
    for offset in range(horizon):
        current = start_date + timedelta(days=offset)
        day_name = _WEEKDAY_NAMES[current.weekday()]
        entry = by_day.get(day_name)
        if entry is None:
            continue
        slots.append(
            PublishingSlot(
                slot_id=f"slot-{current.isoformat()}-{day_name}",
                slot_date=current.isoformat(),
                slot_type=entry["type"],
                lane=entry["lane"],
            )
        )
    return slots
