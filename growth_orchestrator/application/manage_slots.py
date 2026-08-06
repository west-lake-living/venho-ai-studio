from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any, Optional

import yaml

from growth_orchestrator.domain.publishing_slot import PublishingSlot

_WEEKDAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

DEFAULT_CONFIG_ROOT = Path("config/projects")
DEFAULT_DATA_ROOT = Path("data/projects")


def load_cadence_policy(project: str = "venho_hotel", config_root: Path = DEFAULT_CONFIG_ROOT) -> dict[str, Any]:
    return yaml.safe_load((config_root / project / "growth" / "cadence_policy.yaml").read_text(encoding="utf-8"))


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


def ensure_slot_horizon(
    *,
    project: str = "venho_hotel",
    config_root: Path = DEFAULT_CONFIG_ROOT,
    data_root: Path = DEFAULT_DATA_ROOT,
    slot_store: Optional[Any] = None,
    start_date: Optional[date] = None,
    horizon_days: Optional[int] = None,
) -> dict[str, Any]:
    """Materialise the cadence's rolling horizon of OPEN slots on disk.

    Why this exists (2026-08-06): `generate_slots` had no production caller.
    `run_weekly_cycle` created exactly the four slots of the week it was
    about to fill, so every slot it created was consumed in the same run and
    the table never held a single OPEN row -- while `check_runway` counts
    OPEN slots over 14 days and therefore reported `empty` (a real CRITICAL
    Telegram alert) no matter how healthy the system was. The runway canary
    was measuring something nothing produced.

    Idempotent: slot_ids are deterministic and `ensure_slots` is INSERT OR
    IGNORE, so re-running never disturbs a slot that has already been filled
    or missed.
    """
    from shared.jobs.slot_store import SlotStore

    policy = load_cadence_policy(project, config_root)
    store = slot_store or SlotStore(db_path=data_root / project / "growth" / "growth.db")
    slots = generate_slots(policy, start_date=start_date or date.today(), horizon_days=horizon_days)
    inserted = store.ensure_slots(slots)
    return {
        "horizon_days": horizon_days if horizon_days is not None else policy["slot_creation_horizon_days"],
        "slots_in_horizon": len(slots),
        "slots_created": inserted,
    }
