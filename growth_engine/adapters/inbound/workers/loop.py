from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import datetime, time as wall_time, timedelta, timezone
from typing import Callable, Protocol
from zoneinfo import ZoneInfo


_ICT = ZoneInfo("Asia/Ho_Chi_Minh")
_WEEKDAYS = {name: index for index, name in enumerate(("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"))}
_CRON = re.compile(r"(?:(MON|TUE|WED|THU|FRI|SAT|SUN) )?([01][0-9]|2[0-3]):([0-5][0-9])\Z")


class WorkerClock(Protocol):
    def now_ms(self) -> int: ...


@dataclass(frozen=True)
class PeriodicTask:
    """One synchronous task, scheduled by a fixed interval or a local ICT wall time."""

    name: str
    fn: Callable[[], object]
    interval_s: int | None = None
    cron_ict: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip() or not callable(self.fn):
            raise ValueError("task name and callable fn are required")
        if (self.interval_s is None) == (self.cron_ict is None):
            raise ValueError("configure exactly one of interval_s or cron_ict")
        if self.interval_s is not None and (type(self.interval_s) is not int or self.interval_s <= 0):
            raise ValueError("interval_s must be a positive integer")
        if self.cron_ict is not None and _CRON.fullmatch(self.cron_ict) is None:
            raise ValueError("cron_ict must be HH:MM or DAY HH:MM in Asia/Ho_Chi_Minh")

    def next_after(self, at_ms: int) -> int:
        if type(at_ms) is not int:
            raise ValueError("at_ms must be an integer epoch millisecond")
        if self.interval_s is not None:
            return at_ms + self.interval_s * 1000

        assert self.cron_ict is not None
        match = _CRON.fullmatch(self.cron_ict)
        assert match is not None
        day_name, hour_text, minute_text = match.groups()
        hour, minute = int(hour_text), int(minute_text)
        current = datetime.fromtimestamp(at_ms / 1000, timezone.utc).astimezone(_ICT)
        target_day = _WEEKDAYS.get(day_name) if day_name else None
        for offset in range(8):
            candidate_date = current.date() + timedelta(days=offset)
            if target_day is not None and candidate_date.weekday() != target_day:
                continue
            candidate = datetime.combine(candidate_date, wall_time(hour, minute), _ICT)
            candidate_ms = int(candidate.timestamp() * 1000)
            if candidate_ms > at_ms:
                return candidate_ms
        raise RuntimeError("could not calculate the next ICT cron time")


class WorkerLoop:
    """Small deterministic scheduler; task failures are reported and do not stop the loop."""

    def __init__(
        self,
        tasks: tuple[PeriodicTask, ...] | list[PeriodicTask],
        clock: WorkerClock,
        *,
        sleep: Callable[[float], object] = time.sleep,
        on_error: Callable[[PeriodicTask, Exception], object] | None = None,
    ) -> None:
        if len({task.name for task in tasks}) != len(tasks):
            raise ValueError("worker task names must be unique")
        self._tasks = tuple(tasks)
        self._clock = clock
        self._sleep = sleep
        self._on_error = on_error or (lambda _task, _error: None)

    def run_until(self, until_ms: int) -> None:
        """Run scheduled occurrences through `until_ms`, inclusive."""
        if type(until_ms) is not int:
            raise ValueError("until_ms must be an integer epoch millisecond")
        now_ms = self._clock.now_ms()
        if until_ms < now_ms:
            raise ValueError("until_ms must not precede the worker clock")
        due = {task.name: task.next_after(now_ms) for task in self._tasks}

        while due:
            task = min(self._tasks, key=lambda item: due[item.name])
            next_at = due[task.name]
            if next_at > until_ms:
                return
            now_ms = self._clock.now_ms()
            if next_at > now_ms:
                self._sleep((next_at - now_ms) / 1000)
                now_ms = self._clock.now_ms()
                if now_ms < next_at:
                    raise RuntimeError("worker sleep did not advance the clock to the scheduled time")
            if now_ms > until_ms:
                return
            try:
                task.fn()
            except Exception as error:
                try:
                    self._on_error(task, error)
                except Exception:
                    # A failed incident sink must not terminate unrelated worker tasks.
                    pass
            due[task.name] = task.next_after(self._clock.now_ms())

    def run_forever(self) -> None:
        """Run until the process is stopped."""
        while True:
            next_at = min(
                (task.next_after(self._clock.now_ms()) for task in self._tasks),
                default=None,
            )
            if next_at is None:
                self._sleep(60)
                continue
            self.run_until(next_at)
