from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, time

from growth_engine.domain.kernel.time import BusinessCalendar


@dataclass(frozen=True)
class CadenceRule:
    weekday: int
    slot_type: str
    lane: str

    def __post_init__(self) -> None:
        if type(self.weekday) is not int or not 0 <= self.weekday <= 6:
            raise ValueError("weekday must be in the range Monday=0 through Sunday=6")
        if self.slot_type not in {"regular", "special"} or not self.lane.strip():
            raise ValueError("slot_type and lane are invalid")


@dataclass(frozen=True)
class CadencePolicy:
    version: int
    project_id: str
    timezone: str
    publish_time: str
    rules: tuple[CadenceRule, ...]
    window_minutes: int = 30

    def __post_init__(self) -> None:
        if type(self.version) is not int or self.version != 2:
            raise ValueError("cadence policy version must be 2")
        if any(not value.strip() for value in (self.project_id, self.timezone)):
            raise ValueError("project_id and timezone are required")
        parsed_time = time.fromisoformat(self.publish_time)
        if parsed_time.tzinfo is not None:
            raise ValueError("publish_time must be local wall time without timezone")
        if type(self.window_minutes) is not int or self.window_minutes <= 0:
            raise ValueError("window_minutes must be positive")
        weekdays = [rule.weekday for rule in self.rules]
        if len(weekdays) != len(set(weekdays)):
            raise ValueError("cadence rules must have unique weekdays")


@dataclass(frozen=True)
class PlannedSlot:
    project_id: str
    local_date: date
    local_time: str
    timezone: str
    lane: str
    slot_type: str
    cadence_version: str
    scheduled_at_ms: int
    deadline_at_ms: int


def plan_slots(
    policy: CadencePolicy,
    start_date: date,
    horizon_days: int,
    calendar: BusinessCalendar,
) -> list[PlannedSlot]:
    if isinstance(start_date, datetime) or not isinstance(start_date, date):
        raise ValueError("start_date must be a date")
    if type(horizon_days) is not int or horizon_days < 0:
        raise ValueError("horizon_days must be a non-negative integer")
    if calendar.tz != policy.timezone:
        raise ValueError("calendar timezone must match cadence policy")

    by_weekday = {rule.weekday: rule for rule in policy.rules}
    slots: list[PlannedSlot] = []
    for offset in range(horizon_days):
        local_date = start_date + timedelta(days=offset)
        rule = by_weekday.get(local_date.weekday())
        if rule is None:
            continue
        scheduled_at_ms = int(calendar.local_to_epoch_ms(local_date, policy.publish_time))
        slots.append(
            PlannedSlot(
                project_id=policy.project_id,
                local_date=local_date,
                local_time=policy.publish_time,
                timezone=policy.timezone,
                lane=rule.lane,
                slot_type=rule.slot_type,
                cadence_version=str(policy.version),
                scheduled_at_ms=scheduled_at_ms,
                deadline_at_ms=scheduled_at_ms + policy.window_minutes * 60_000,
            )
        )
    return slots
