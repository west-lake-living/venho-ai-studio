from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol, Sequence
from zoneinfo import ZoneInfo

from growth_engine.application.ops.notifications import NotificationQueue
from growth_engine.domain.delivery.states import DeliveryState


@dataclass(frozen=True)
class ReminderCandidate:
    delivery_id: str
    revision_id: str
    state: DeliveryState
    scheduled_at_ms: int
    topic: str
    page_names: tuple[str, ...]
    deadline_label: str


@dataclass(frozen=True)
class DailyDigest:
    ready: int
    total: int
    awaiting: int
    attention: int
    tomorrow_label: str


class ReminderRepository(Protocol):
    def due_reminders(
        self,
        *,
        now_ms: int,
        reminder_offsets_minutes: Sequence[int],
        window_minutes: int,
    ) -> Sequence[ReminderCandidate]: ...

    def reserve_if_current(
        self,
        candidate: ReminderCandidate,
        *,
        reminder_kind: str,
        message: str,
        now_ms: int,
    ) -> bool: ...

    def daily_digest(self, now_ms: int) -> DailyDigest: ...


@dataclass(frozen=True)
class ReminderPolicy:
    timezone: str = "Asia/Ho_Chi_Minh"
    reminder_offsets_minutes: tuple[int, ...] = (1440, 360)
    window_minutes: int = 15
    digest_local_time: str = "20:00"
    dashboard_base_url: str = ""


class Reminders:
    def __init__(
        self,
        repository: ReminderRepository,
        queue: NotificationQueue,
        policy: ReminderPolicy,
    ) -> None:
        self._repository = repository
        self._queue = queue
        self._policy = policy
        self._zone = ZoneInfo(policy.timezone)

    def tick(self, now_ms: int) -> tuple[str, ...]:
        offsets = self._policy.reminder_offsets_minutes
        candidates = self._repository.due_reminders(
            now_ms=now_ms,
            reminder_offsets_minutes=offsets,
            window_minutes=self._policy.window_minutes,
        )
        reserved: list[str] = []
        for candidate in candidates:
            if candidate.state is not DeliveryState.IN_REVIEW:
                continue
            scheduled = candidate.scheduled_at_ms
            minutes_before = min(offsets, key=lambda offset: abs((scheduled - now_ms) // 60_000 - offset))
            if abs((scheduled - now_ms) - minutes_before * 60_000) > self._policy.window_minutes * 60_000:
                continue
            kind = "T24" if minutes_before >= 1440 else "T6"
            link = _review_link(self._policy.dashboard_base_url, candidate.delivery_id)
            hours = minutes_before // 60
            message = (
                f"⏰ Còn {hours} giờ — 1 bài chưa duyệt cho {candidate.deadline_label}\n"
                f"👉 {link}"
            )
            if self._repository.reserve_if_current(
                candidate,
                reminder_kind=kind,
                message=message,
                now_ms=now_ms,
            ):
                reserved.append(f"{candidate.delivery_id}:{candidate.revision_id}:{kind}")
        return tuple(reserved)

    def enqueue_daily_digest(self, now_ms: int) -> str | None:
        local = datetime.fromtimestamp(now_ms / 1000, self._zone)
        if local.strftime("%H:%M") != self._policy.digest_local_time:
            return None
        digest = self._repository.daily_digest(now_ms)
        message = (
            f"📋 Ngày mai {digest.tomorrow_label}: {digest.ready}/{digest.total} bài sẵn sàng · "
            f"{digest.awaiting} chờ duyệt · {digest.attention} cần xử lý"
        )
        return self._queue.enqueue_unique(
            f"daily-digest:{local.date().isoformat()}", message, created_at_ms=now_ms
        )


def _review_link(base_url: str, delivery_id: str) -> str:
    if not base_url.startswith("https://"):
        raise ValueError("dashboard base URL must be HTTPS")
    return f"{base_url.rstrip('/')}/growth/deliveries/{delivery_id}"
