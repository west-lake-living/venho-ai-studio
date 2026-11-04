from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import NewType
from zoneinfo import ZoneInfo


EpochMs = NewType("EpochMs", int)
_UTC_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


class BusinessCalendar:
    """Convert between a business timezone and UTC epoch milliseconds."""

    def __init__(self, tz: str = "Asia/Ho_Chi_Minh") -> None:
        self.tz = tz
        self._zone = ZoneInfo(tz)

    def local_to_epoch_ms(self, local_date: date, local_time: str) -> EpochMs:
        if isinstance(local_date, datetime) or not isinstance(local_date, date):
            raise TypeError("local_date must be a date")
        parsed_time = time.fromisoformat(local_time)
        if parsed_time.tzinfo is not None:
            raise ValueError("local_time must not include a timezone")
        local_datetime = datetime.combine(local_date, parsed_time, tzinfo=self._zone)
        delta = local_datetime.astimezone(timezone.utc) - _UTC_EPOCH
        value = (delta.days * 86_400 + delta.seconds) * 1_000 + delta.microseconds // 1_000
        return EpochMs(value)

    def epoch_ms_to_local(self, epoch_ms: int) -> datetime:
        if isinstance(epoch_ms, bool) or not isinstance(epoch_ms, int):
            raise TypeError("epoch_ms must be an integer")
        utc_datetime = _UTC_EPOCH + timedelta(milliseconds=epoch_ms)
        return utc_datetime.astimezone(self._zone)

    def period_key(self, epoch_ms: int) -> str:
        return self.epoch_ms_to_local(epoch_ms).strftime("%Y-%m")
