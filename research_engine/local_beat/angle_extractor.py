from __future__ import annotations

from collections.abc import Callable
from typing import Any

from research_engine.local_beat.entities import BeatItem, GuestAngle


AngleProvider = Callable[[BeatItem], dict[str, Any]]


def extract_guest_angle(
    item: BeatItem,
    provider: AngleProvider | None = None,
    *,
    active_fact_ids_r3: set[str] | None = None,
) -> GuestAngle | None:
    """Validate provider output strictly; never repair malformed LLM JSON."""
    if provider is None:
        return None
    try:
        payload = provider(item)
        angle = GuestAngle.from_payload(payload)
        if active_fact_ids_r3 is not None and not set(angle.fact_ids_r3).issubset(active_fact_ids_r3):
            return None
        return angle
    except (TypeError, ValueError, KeyError):
        return None
