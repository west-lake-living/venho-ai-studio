# STATUS (2026-08-06): wired into growth_orchestrator.application.daily_cycle
# ._fill_slot_from_evergreen -- called when every platform's real generation
# attempt has failed for a slot, before that slot is allowed to go MISSED
# (Phase 4.5, §9.3 "Evergreen Pool — mạng an toàn"). Population is entirely
# manual (`shared/storage/evergreen_pool_store.py` + CLI `evergreen-add`) --
# the pool is empty by default and this fallback simply never fires until
# Harry curates items into it.
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
