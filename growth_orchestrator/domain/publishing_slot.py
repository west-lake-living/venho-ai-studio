from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


PublishingSlotStatus = Literal[
    "OPEN",
    "DRAFT_ASSIGNED",
    "PENDING_APPROVAL",
    "FILLED",
    "DISPATCHED",
    "COMPLETED",
    "EVERGREEN_FALLBACK",
    "MISSED",
]

SlotType = Literal["regular", "special"]
Lane = Literal["regular", "special", "evergreen", "blog_seo"]


class PublishingSlot(BaseModel):
    slot_id: str
    slot_date: str
    slot_type: SlotType
    lane: Lane
    status: PublishingSlotStatus = "OPEN"
    content_package_id: Optional[str] = None
    filled_from: Optional[Literal["pipeline", "evergreen"]] = None

    def transition(self, target: PublishingSlotStatus, **updates: object) -> "PublishingSlot":
        allowed: dict[str, set[str]] = {
            "OPEN": {"DRAFT_ASSIGNED", "EVERGREEN_FALLBACK", "MISSED"},
            # DRAFT_ASSIGNED -> EVERGREEN_FALLBACK / MISSED: every platform's
            # generation attempt failed after a draft was assigned to this
            # slot (no surviving content to review) -- this is the real path
            # daily_cycle hits (evergreen_pool.py is wired in as of
            # 2026-08-06, see daily_cycle._fill_slot_from_evergreen).
            "DRAFT_ASSIGNED": {"PENDING_APPROVAL", "EVERGREEN_FALLBACK", "MISSED"},
            "PENDING_APPROVAL": {"FILLED", "DRAFT_ASSIGNED"},
            "FILLED": {"DISPATCHED"},
            # EVERGREEN_FALLBACK -> PENDING_APPROVAL (not straight to
            # DISPATCHED, unlike the plan's original §9.3 draft): Harry
            # decided 2026-08-06 that a reused evergreen post still needs
            # one Duyệt click, same as any other draft -- no code path may
            # publish without that click (DoD #23 invariant), even for
            # content that was approved once before, since a full evergreen
            # story runs FILLED/DISPATCHED through the same funnel as a
            # fresh draft once it lands back in PENDING_APPROVAL.
            "EVERGREEN_FALLBACK": {"PENDING_APPROVAL"},
            "DISPATCHED": {"COMPLETED"},
        }
        if target not in allowed.get(self.status, set()):
            raise ValueError(f"Invalid PublishingSlot transition: {self.status} -> {target}")
        return self.model_copy(update={"status": target, **updates})

    def assert_missed_only_after_evergreen_exhausted(self, *, evergreen_exhausted: bool) -> None:
        """Guard the real MISSED path (from OPEN or DRAFT_ASSIGNED -- the
        only two states MISSED is reachable from, see `transition`'s allowed
        map) rather than only OPEN. Before 2026-08-06 this only checked
        `self.status != "OPEN"`, which never fired for the actual
        `daily_cycle` failure path (DRAFT_ASSIGNED), making the guard dead
        code in production even though its unit test passed.
        """
        if self.status not in ("OPEN", "DRAFT_ASSIGNED"):
            return
        if not evergreen_exhausted:
            raise ValueError("Slot cannot be MISSED before the evergreen pool has been exhausted")
