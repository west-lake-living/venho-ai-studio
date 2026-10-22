from __future__ import annotations

"""Close publishing slots whose date has passed from what the registry says
actually happened (Lỗi #10, Harry 2026-10-22).

Slots used to stay PENDING_APPROVAL forever when their drafts FAILED, were
replaced or expired (11/09, 12/09, 07/10), and four August slots read MISSED
although a post went out. Nothing ran after the day to settle them.
"""

from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

from publishing_gateway.publication_registry import PublicationRegistry
from shared.jobs.slot_store import SlotStore

# GATEWAY_ACCEPTED: Make took the post but its route sends no confirmation
# back (see make_gateway.interpret_make_response) -- it went out.
SENT_STATUSES = {"PUBLISHED", "GATEWAY_ACCEPTED"}
# Every row of the slot was withdrawn on purpose (Harry cancelled it), so the
# empty day was planned rather than a failure.
ALL_CANCELLED = "all_cancelled"


def reconcile_slots(
    *,
    project: str = "venho_hotel",
    data_root: Path = Path("data/projects"),
    today: Optional[date] = None,
) -> list[dict[str, Any]]:
    today = today or datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()
    store = SlotStore(db_path=data_root / project / "growth" / "growth.db")
    statuses: dict[str, set[str]] = defaultdict(set)
    for row in PublicationRegistry(project, data_root=data_root).load()["publications"]:
        if row.get("slot_id"):
            statuses[row["slot_id"]].add(str(row.get("status")))

    changes = []
    for slot in store.list_all():
        if slot.slot_date >= today.isoformat():
            continue
        seen = statuses.get(slot.slot_id, set())
        if seen & SENT_STATUSES:
            target, reason = "COMPLETED", "published"
        elif seen and seen <= {"CANCELLED"}:
            target, reason = "MISSED", ALL_CANCELLED
        else:
            target, reason = "MISSED", "no_publication:" + (",".join(sorted(seen)) or "none")
        if slot.status == target:
            continue
        store.close_past_slot(slot.slot_id, target, reason=reason)
        changes.append({"slot_id": slot.slot_id, "from": slot.status, "to": target, "reason": reason})
    return changes
