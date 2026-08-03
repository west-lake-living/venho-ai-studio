from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from shared.budget.ledger import BudgetLedger, BudgetPolicy
from shared.jobs.job_store import JobStore
from shared.jobs.scheduler import enqueue_idempotent_dispatch, lateness_alert, next_dispatch_at
from shared.jobs.worker import Worker


def test_duplicate_scheduler_trigger_creates_one_job(tmp_path) -> None:
    store = JobStore(tmp_path / "growth.db")
    scheduled_at = next_dispatch_at(datetime(2026, 8, 4).date())

    keys = [
        enqueue_idempotent_dispatch(store, publication_id="pub-1", scheduled_at=scheduled_at, trace_id=f"trace-{index}")
        for index in range(5)
    ]

    assert len(set(keys)) == 1
    assert store.count_by_idempotency_key(keys[0]) == 1


def test_worker_heartbeat_and_restart_recovery(tmp_path) -> None:
    store = JobStore(tmp_path / "growth.db")
    scheduled_at = (datetime.now() - timedelta(seconds=1)).isoformat()
    store.enqueue(
        job_id="job-heartbeat",
        idempotency_key="heartbeat-key",
        job_type="daily_dispatch",
        version="1",
        scheduled_at=scheduled_at,
        trace_id="trace-heartbeat",
        payload={},
    )
    worker = Worker("worker-a", store)
    job = store.claim(owner=worker.owner, lease_seconds=-1)
    assert job["id"] == "job-heartbeat"

    assert worker.heartbeat("job-heartbeat", lease_seconds=120) is True
    assert store.recover_expired_leases() == 0

    assert store.heartbeat("job-heartbeat", owner="worker-a", lease_seconds=-1) is True
    assert worker.recover() == 1
    assert store.claim(owner="worker-b")["id"] == "job-heartbeat"


def test_retry_matrix_requeues_retryable_failures(tmp_path) -> None:
    store = JobStore(tmp_path / "growth.db")
    scheduled_at = (datetime.now() - timedelta(seconds=1)).isoformat()
    store.enqueue(
        job_id="job-retry",
        idempotency_key="retry-key",
        job_type="daily_dispatch",
        version="1",
        scheduled_at=scheduled_at,
        trace_id="trace-retry",
        payload={},
        max_attempt=2,
    )
    claimed = store.claim(owner="worker-a")
    store.fail(claimed["id"], "temporary failure")
    assert store.get("job-retry")["status"] == "RETRYABLE_FAILED"

    assert store.requeue_retryable_failures({1: 0}) == 1
    assert store.claim(owner="worker-b")["id"] == "job-retry"
    store.fail("job-retry", "second failure")
    assert store.get("job-retry")["status"] == "TERMINAL_FAILED"


def test_late_run_has_alert() -> None:
    scheduled_at = "2026-08-03T09:00:00+07:00"
    now = datetime(2026, 8, 3, 9, 16, tzinfo=timezone(timedelta(hours=7)))

    alert = lateness_alert(scheduled_at, now=now, grace_minutes=10)

    assert alert["alert"] == "LATE_RUN"
    assert alert["late_by_seconds"] == 960


def test_budget_threshold_alerts_and_cap_block_with_override(tmp_path) -> None:
    ledger = BudgetLedger(tmp_path / "growth.db")
    policy = BudgetPolicy(monthly_cap_minor=1000, alert_thresholds=[0.7, 0.85, 1.0])

    ledger.commit("spent", 840)
    evaluation = policy.reserve_paid_call(ledger, "reserve-1", 10)
    assert evaluation["alerts"] == ["BUDGET_70", "BUDGET_85"]
    ledger.release("reserve-1", 10)

    with pytest.raises(ValueError, match="budget cap reached"):
        policy.reserve_paid_call(ledger, "reserve-blocked", 200)

    override_eval = policy.reserve_paid_call(
        ledger,
        "reserve-override",
        200,
        override={"reason": "manual launch window", "approved_by": "harry"},
    )
    assert override_eval["blocked"] is True
    assert ledger.overrides()[0]["approved_by"] == "harry"
