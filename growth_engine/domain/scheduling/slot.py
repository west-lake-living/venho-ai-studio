from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class Slot:
    id: str
    project_id: str
    local_date: date
    local_time: str
    timezone: str
    lane: str
    cadence_version: str
    scheduled_at_ms: int
    deadline_at_ms: int
    cancelled_at_ms: int | None = None

    def __post_init__(self) -> None:
        for name in ("id", "project_id", "local_time", "timezone", "lane", "cadence_version"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} is required")
        if isinstance(self.local_date, datetime) or not isinstance(self.local_date, date):
            raise ValueError("local_date must be a date")
        if type(self.scheduled_at_ms) is not int or type(self.deadline_at_ms) is not int:
            raise ValueError("slot timestamps must be integer epoch milliseconds")
        if self.deadline_at_ms < self.scheduled_at_ms:
            raise ValueError("deadline_at_ms must not precede scheduled_at_ms")
        if self.cancelled_at_ms is not None and type(self.cancelled_at_ms) is not int:
            raise ValueError("cancelled_at_ms must be an integer or None")


@dataclass(frozen=True)
class SlotTarget:
    id: str
    slot_id: str
    channel_id: str
    required: bool = True

    def __post_init__(self) -> None:
        for name in ("id", "slot_id", "channel_id"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} is required")
        if type(self.required) is not bool:
            raise ValueError("required must be a boolean")
