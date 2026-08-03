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
