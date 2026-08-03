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
            "DRAFT_ASSIGNED": {"PENDING_APPROVAL"},
            "PENDING_APPROVAL": {"FILLED", "DRAFT_ASSIGNED"},
            "FILLED": {"DISPATCHED"},
            "EVERGREEN_FALLBACK": {"DISPATCHED"},
            "DISPATCHED": {"COMPLETED"},
        }
        if target not in allowed.get(self.status, set()):
            raise ValueError(f"Invalid PublishingSlot transition: {self.status} -> {target}")
        return self.model_copy(update={"status": target, **updates})

    def assert_missed_only_after_evergreen_exhausted(self, *, evergreen_exhausted: bool) -> None:
        if self.status != "OPEN":
            return
        if not evergreen_exhausted:
            raise ValueError("Slot cannot be MISSED before the evergreen pool has been exhausted")
