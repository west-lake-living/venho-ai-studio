from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from growth_engine.adapters.outbound.notify.telegram_notifier import TelegramDeliveryError, TelegramNotifier
from growth_engine.application.ops.notifications import NotificationJob, Notifications
from growth_engine.application.ops.reminders import DailyDigest, ReminderCandidate, ReminderPolicy, Reminders
from growth_engine.domain.delivery.states import DeliveryState


class Clock:
    def __init__(self, now_ms: int) -> None:
        self.value = now_ms

    def now_ms(self) -> int:
        return self.value


class Queue:
    def __init__(self) -> None:
        self.jobs: dict[str, NotificationJob] = {}
        self.sent: set[str] = set()
        self.retries: list[tuple[str, int, str]] = []

    def enqueue_unique(self, dedupe_key: str, message: str, *, created_at_ms: int) -> str | None:
        if dedupe_key in self.jobs:
            return None
        job = NotificationJob(f"synthetic-job-{len(self.jobs) + 1}", dedupe_key, message)
        self.jobs[dedupe_key] = job
        return job.id

    def claim_pending(self, *, limit: int, now_ms: int):
        return tuple(job for job in self.jobs.values() if job.id not in self.sent)[:limit]

    def mark_sent(self, job_id: str, *, sent_at_ms: int) -> None:
        self.sent.add(job_id)

    def schedule_retry(self, job_id: str, *, retry_at_ms: int, error_type: str) -> None:
        self.retries.append((job_id, retry_at_ms, error_type))


class Sender:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.messages: list[str] = []

    def send(self, message: str) -> None:
        if self.fail:
            raise RuntimeError("synthetic transport outage")
        self.messages.append(message)


def test_same_incident_ten_ticks_enqueues_only_one_message() -> None:
    queue = Queue()
    sender = Sender()
    service = Notifications(queue, sender, Clock(1_800_000_000_000))
    for _ in range(10):
        service.enqueue_incident(
            incident_id="synthetic-incident",
            incident_type="UNKNOWN",
            delivery_id="synthetic-delivery",
            page_name="Synthetic Page",
            scheduled_label="Thứ Hai 01/01 09:00",
            reconcile_link="https://dashboard.example.invalid/growth/deliveries/synthetic-delivery",
            created_at_ms=1_800_000_000_000,
        )
        service.dispatch()

    assert len(queue.jobs) == 1
    assert len(sender.messages) == 1
    assert "KHÔNG tự đăng lại" in sender.messages[0]


def test_telegram_failure_schedules_retry_without_throwing_or_rolling_back() -> None:
    queue = Queue()
    sender = Sender(fail=True)
    service = Notifications(queue, sender, Clock(1_800_000_000_000))
    job_id = service.enqueue_incident(
        incident_id="synthetic-incident",
        incident_type="UNKNOWN",
        delivery_id="synthetic-delivery",
        page_name="Synthetic Page",
        scheduled_label="Synthetic schedule",
        reconcile_link="https://dashboard.example.invalid/growth/deliveries/synthetic-delivery",
        created_at_ms=1_800_000_000_000,
    )

    result = service.dispatch()

    assert result.retried == (job_id,)
    assert queue.retries[0][0] == job_id
    assert queue.sent == set()


def test_published_message_links_to_delivery_id() -> None:
    queue = Queue()
    service = Notifications(queue, Sender(), Clock(1_800_000_000_000))

    job_id = service.enqueue_published(
        delivery_id="delivery-123",
        page_name="Synthetic Page",
        scheduled_label="Thứ Hai 01/01 09:00",
        permalink="https://facebook.example.invalid/post/123",
        quality_label="PASS",
        created_at_ms=1_800_000_000_000,
    )

    assert job_id is not None
    assert queue.jobs["published:delivery-123"].dedupe_key == "published:delivery-123"


class ReminderRepo:
    def __init__(self, candidates=()) -> None:
        self.candidates = tuple(candidates)
        self.current = {candidate.delivery_id: (candidate.revision_id, candidate.state) for candidate in candidates}
        self.reserved: list[tuple[str, str, str]] = []

    def due_reminders(self, **kwargs):
        return self.candidates

    def reserve_if_current(self, candidate, *, reminder_kind: str, message: str, now_ms: int) -> bool:
        if self.current.get(candidate.delivery_id) != (candidate.revision_id, DeliveryState.IN_REVIEW):
            return False
        if any(item[0] == candidate.delivery_id and item[1] == reminder_kind for item in self.reserved):
            return False
        self.reserved.append((candidate.delivery_id, reminder_kind, message))
        return True

    def daily_digest(self, now_ms: int) -> DailyDigest:
        return DailyDigest(ready=2, total=4, awaiting=1, attention=1, tomorrow_label="Thứ Ba 05/11")


def test_reminders_skip_approved_cancelled_and_changed_revision() -> None:
    now_ms = 1_800_000_000_000
    scheduled = now_ms + 24 * 60 * 60_000
    approved = ReminderCandidate("approved", "r1", DeliveryState.APPROVED, scheduled, "topic", ("Page",), "label")
    changed = ReminderCandidate("changed", "r1", DeliveryState.IN_REVIEW, scheduled, "topic", ("Page",), "label")
    repo = ReminderRepo([approved, changed])
    repo.current["changed"] = ("r2", DeliveryState.IN_REVIEW)
    queue = Queue()
    service = Reminders(repo, queue, ReminderPolicy(dashboard_base_url="https://dashboard.example.invalid"))

    result = service.tick(now_ms)

    assert result == ()
    assert repo.reserved == []


def test_t24_and_t6_reminder_and_20_00_digest_are_deduplicated() -> None:
    zone = ZoneInfo("Asia/Ho_Chi_Minh")
    local_now = datetime(2026, 11, 4, 20, 0, tzinfo=zone)
    now_ms = int(local_now.timestamp() * 1000)
    candidate_24 = ReminderCandidate("delivery-24", "r1", DeliveryState.IN_REVIEW, now_ms + 24 * 60 * 60_000, "topic", ("Page",), "tomorrow")
    candidate_6 = ReminderCandidate("delivery-6", "r1", DeliveryState.IN_REVIEW, now_ms + 6 * 60 * 60_000, "topic", ("Page",), "tonight")
    repo = ReminderRepo([candidate_24, candidate_6])
    queue = Queue()
    service = Reminders(
        repo,
        queue,
        ReminderPolicy(dashboard_base_url="https://dashboard.example.invalid"),
    )

    reserved = service.tick(now_ms)
    digest_one = service.enqueue_daily_digest(now_ms)
    digest_two = service.enqueue_daily_digest(now_ms)

    assert len(reserved) == 2
    assert {item[1] for item in repo.reserved} == {"T24", "T6"}
    assert digest_one is not None
    assert digest_two is None
    assert "2/4 bài sẵn sàng" in queue.jobs["daily-digest:2026-11-04"].message


class FakeTelegramTransport:
    def __init__(self, status: int = 200, response: bytes = b'{"ok":true}') -> None:
        self.status = status
        self.response = response
        self.url = ""
        self.payload = b""

    def post(self, url: str, body: bytes, *, timeout: float):
        self.url = url
        self.payload = body
        return self.status, self.response


def test_telegram_notifier_redacts_credentials_and_uses_fake_transport() -> None:
    transport = FakeTelegramTransport()
    notifier = TelegramNotifier("synthetic-bot-token", "synthetic-chat-id", transport)

    notifier.send("synthetic message")

    assert "synthetic-bot-token" not in repr(notifier)
    assert json.loads(transport.payload)["text"] == "synthetic message"

    rejected = TelegramNotifier(
        "synthetic-bot-token", "synthetic-chat-id", FakeTelegramTransport(403, b'{"ok":false}')
    )
    try:
        rejected.send("synthetic message")
    except TelegramDeliveryError as error:
        assert "synthetic-bot-token" not in str(error)
    else:
        raise AssertionError("Telegram rejection must be surfaced to the retry queue")
