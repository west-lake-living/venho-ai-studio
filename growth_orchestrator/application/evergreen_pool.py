# STATUS (2026-08-05 audit): implemented and unit-tested (Phase 4.5, §9.3
# "Evergreen Pool — mạng an toàn") but NOT wired into any real caller yet.
# `publishing_slot.py` references it only in a comment ("still applies once
# evergreen_pool.py is wired in") -- the MISSED-requires-evergreen-exhausted
# transition currently has no real evergreen pool feeding it. Wire this in
# before relying on the "slot never goes MISSED while evergreen has stock"
# guarantee in production.
from __future__ import annotations

from datetime import date, datetime


def choose_evergreen(items: list[dict], today: date | None = None, cooldown_days: int = 90) -> dict | None:
    now = today or date.today()
    for item in items:
        if item.get("status") != "approved":
            continue
        last_used = item.get("last_used_at")
        if not last_used:
            return item
        if (now - datetime.fromisoformat(last_used).date()).days >= cooldown_days:
            return item
    return None
