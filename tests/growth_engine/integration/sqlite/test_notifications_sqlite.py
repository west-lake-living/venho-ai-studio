from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from growth_engine.adapters.outbound.persistence.sqlite.notifications import (
    SqliteNotificationQueue,
    SqliteReminderRepository,
)
from growth_engine.adapters.outbound.persistence.sqlite.repositories.jobs import JobRecord
from growth_engine.application.ops.notifications import Notifications
from growth_engine.application.ops.reminders import ReminderCandidate
from growth_engine.domain.delivery.states import DeliveryState
from tests.growth_engine.integration.sqlite.test_revision_store import _fixture
from tests.growth_engine.support.fakes import SeqIds


class _Clock:
    def __init__(self, now_ms: int) -> None:
        self.value = now_ms

    def now_ms(self) -> int:
        return self.value


class _FailThenSucceedSender:
    def __init__(self) -> None:
        self.calls = 0

    def send(self, _message: str) -> None:
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("synthetic Telegram outage")


def test_sqlite_notification_jobs_are_deduplicated_leased_retried_and_completed(tmp_path: Path) -> None:
    _database, uow_factory, _slot, _variant, _caption, _revision = _fixture(tmp_path)
    queue = SqliteNotificationQueue(uow_factory, SeqIds("notify"), lease_ms=100)
    first = queue.enqueue_unique("incident:one", "synthetic notice", created_at_ms=10)
    replay = queue.enqueue_unique("incident:one", "synthetic notice", created_at_ms=11)
    assert first is not None and replay is None

    claimed = queue.claim_pending(limit=10, now_ms=10)
    assert len(claimed) == 1 and claimed[0].id == first
    competing_worker = SqliteNotificationQueue(uow_factory, SeqIds("other"), lease_ms=100)
    assert competing_worker.claim_pending(limit=10, now_ms=20) == ()
    queue.schedule_retry(first, retry_at_ms=200, error_type="SyntheticError")
    with uow_factory().read_only() as tx:
        row = tx.jobs.get(first)
    assert row is not None
    assert (row.state, row.attempts, row.run_at_ms, row.last_error) == (
        "PENDING", 1, 200, "notify:SyntheticError"
    )

    claimed_retry = queue.claim_pending(limit=10, now_ms=200)
    assert len(claimed_retry) == 1 and claimed_retry[0].id == first
    queue.mark_sent(first, sent_at_ms=210)
    with uow_factory().read_only() as tx:
        row = tx.jobs.get(first)
    assert row is not None and row.state == "SUCCEEDED" and row.lease_token is None


def test_notifications_service_retries_through_real_sqlite_queue_without_business_rollback(
    tmp_path: Path,
) -> None:
    _database, uow_factory, _slot, _variant, _caption, _revision = _fixture(tmp_path)
    clock = _Clock(1_800_000_000_000)
    queue = SqliteNotificationQueue(uow_factory, SeqIds("notify"))
    sender = _FailThenSucceedSender()
    service = Notifications(queue, sender, clock)
    job_id = service.enqueue_incident(
        incident_id="synthetic-incident",
        incident_type="UNKNOWN",
        delivery_id="synthetic-delivery",
        page_name="Synthetic Page",
        scheduled_label="Synthetic schedule",
        reconcile_link="https://dashboard.example.test/growth/deliveries/synthetic-delivery",
        created_at_ms=clock.now_ms(),
    )

    first = service.dispatch()
    with uow_factory().read_only() as tx:
        retried_job = tx.jobs.get(job_id)
    assert first.retried == (job_id,)
    assert retried_job is not None and retried_job.state == "PENDING"
    assert retried_job.last_error == "notify:RuntimeError"

    clock.value = retried_job.run_at_ms
    second = service.dispatch()
    with uow_factory().read_only() as tx:
        sent_job = tx.jobs.get(job_id)
    assert second.sent == (job_id,)
    assert sent_job is not None and sent_job.state == "SUCCEEDED" and sent_job.attempts == 1
    assert sender.calls == 2


def test_sqlite_review_notification_is_rendered_and_stale_revision_is_cancelled(tmp_path: Path) -> None:
    _database, uow_factory, _slot, _variant, _caption, _revision = _fixture(tmp_path)
    with uow_factory().begin_immediate() as tx:
        tx.connection.execute(
            "UPDATE deliveries SET state='IN_REVIEW', active_approval_id=NULL WHERE id='delivery-synthetic'"
        )
        for job_id, revision_id, created_at in (
            ("notify-current", "revision-a", 10),
            ("notify-stale", "revision-old", 11),
        ):
            tx.jobs.save(JobRecord(
                id=job_id,
                kind="notify",
                lane="publish",
                business_key=f"review:{job_id}",
                payload_json=json.dumps({
                    "type": "REVIEW_NEEDED",
                    "delivery_id": "delivery-synthetic",
                    "revision_id": revision_id,
                }),
                state="PENDING",
                run_at_ms=created_at,
                created_at_ms=created_at,
                updated_at_ms=created_at,
            ))
    queue = SqliteNotificationQueue(
        uow_factory,
        SeqIds("notify"),
        dashboard_base_url="https://dashboard.example.test",
        templates={"review_needed": "Review {topic}: {review_link}"},
    )

    claimed = queue.claim_pending(limit=10, now_ms=20)

    assert len(claimed) == 1
    assert "topic-synthetic" in claimed[0].message
    assert claimed[0].message.endswith("/growth/deliveries/delivery-synthetic")
    with uow_factory().read_only() as tx:
        stale = tx.jobs.get("notify-stale")
    assert stale is not None and stale.state == "CANCELLED"


def test_sqlite_reminder_reservation_rechecks_revision_and_digest_uses_tomorrow_counts(tmp_path: Path) -> None:
    _database, uow_factory, _slot, _variant, _caption, _revision = _fixture(tmp_path)
    now = datetime(2026, 11, 4, 20, 0, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
    now_ms = int(now.timestamp() * 1000)
    scheduled_at = now_ms + 6 * 60 * 60_000
    with uow_factory().begin_immediate() as tx:
        tx.connection.execute(
            "UPDATE deliveries SET state='IN_REVIEW', active_approval_id=NULL WHERE id='delivery-synthetic'"
        )
        tx.connection.execute(
            "UPDATE slots SET scheduled_at=?, deadline_at=? WHERE id='slot-synthetic'",
            (scheduled_at, scheduled_at + 8 * 60 * 60_000),
        )
    repository = SqliteReminderRepository(
        uow_factory, SeqIds("reminder"), environment="test", timezone_name="Asia/Ho_Chi_Minh"
    )

    candidates = repository.due_reminders(
        now_ms=now_ms, reminder_offsets_minutes=(360,), window_minutes=15
    )
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.state is DeliveryState.IN_REVIEW
    assert repository.reserve_if_current(
        candidate, reminder_kind="T6", message="synthetic reminder", now_ms=now_ms
    ) is True
    assert repository.reserve_if_current(
        candidate, reminder_kind="T6", message="synthetic reminder", now_ms=now_ms
    ) is False
    digest = repository.daily_digest(now_ms)
    assert (digest.ready, digest.total, digest.awaiting, digest.attention) == (0, 1, 1, 0)

    with uow_factory().begin_immediate() as tx:
        tx.connection.execute("UPDATE deliveries SET state='CANCELLED' WHERE id='delivery-synthetic'")
    assert repository.reserve_if_current(
        candidate, reminder_kind="T24", message="stale reminder", now_ms=now_ms
    ) is False

