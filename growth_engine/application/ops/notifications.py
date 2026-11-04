from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True)
class NotificationJob:
    id: str
    dedupe_key: str
    message: str
    attempts: int = 0


class NotificationQueue(Protocol):
    def enqueue_unique(self, dedupe_key: str, message: str, *, created_at_ms: int) -> str | None: ...
    def claim_pending(self, *, limit: int, now_ms: int) -> Sequence[NotificationJob]: ...
    def mark_sent(self, job_id: str, *, sent_at_ms: int) -> None: ...
    def schedule_retry(self, job_id: str, *, retry_at_ms: int, error_type: str) -> None: ...


class MessageSender(Protocol):
    def send(self, message: str) -> None: ...


@dataclass(frozen=True)
class NotificationDrainResult:
    sent: tuple[str, ...]
    retried: tuple[str, ...]


class Notifications:
    """Enqueue deduplicated notifications and deliver them outside business writes."""

    def __init__(self, queue: NotificationQueue, sender: MessageSender, clock) -> None:
        self._queue = queue
        self._sender = sender
        self._clock = clock

    def enqueue_incident(
        self,
        *,
        incident_id: str,
        incident_type: str,
        delivery_id: str,
        page_name: str,
        scheduled_label: str,
        reconcile_link: str,
        created_at_ms: int,
    ) -> str | None:
        if not all(value.strip() for value in (incident_id, incident_type, delivery_id)):
            raise ValueError("incident identity is required")
        if incident_type == "UNKNOWN":
            message = f"🔴 Chưa rõ kết quả đăng — {page_name} · {scheduled_label}\nHệ thống KHÔNG tự đăng lại.\n👉 Đối soát: {reconcile_link}"
        else:
            message = f"🟠 Cần xử lý — {page_name} · {scheduled_label}\nMã: {incident_type}\n👉 Mở bài: {reconcile_link}"
        return self._queue.enqueue_unique(
            f"incident:{incident_id}", message, created_at_ms=created_at_ms
        )

    def enqueue_published(
        self,
        *,
        delivery_id: str,
        page_name: str,
        scheduled_label: str,
        permalink: str,
        quality_label: str,
        created_at_ms: int,
    ) -> str | None:
        if not delivery_id.strip():
            raise ValueError("delivery_id is required")
        message = f"✅ Đã đăng — {page_name} · {scheduled_label}\n{permalink}\nXác minh: {quality_label}"
        return self._queue.enqueue_unique(
            f"published:{delivery_id}", message, created_at_ms=created_at_ms
        )

    def dispatch(self, *, limit: int = 50) -> NotificationDrainResult:
        if type(limit) is not int or limit < 1:
            raise ValueError("limit must be positive")
        sent: list[str] = []
        retried: list[str] = []
        for job in self._queue.claim_pending(limit=limit, now_ms=self._clock.now_ms()):
            try:
                self._sender.send(job.message)
            except Exception as error:
                self._queue.schedule_retry(
                    job.id,
                    retry_at_ms=self._clock.now_ms() + min(60, 2 ** min(job.attempts, 6)) * 60_000,
                    error_type=type(error).__name__,
                )
                retried.append(job.id)
            else:
                self._queue.mark_sent(job.id, sent_at_ms=self._clock.now_ms())
                sent.append(job.id)
        return NotificationDrainResult(tuple(sent), tuple(retried))
