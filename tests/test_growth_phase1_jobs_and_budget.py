from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

from shared.budget.ledger import BudgetLedger
from shared.jobs.job_store import JobStore
from shared.jobs.scheduler import next_dispatch_at


def test_job_store_idempotent_enqueue_claim_complete(tmp_path) -> None:
    store = JobStore(tmp_path / "growth.db")
    scheduled_at = (datetime.now() - timedelta(seconds=1)).isoformat()
    store.enqueue(
        job_id="job-1",
        idempotency_key="same-key",
        job_type="daily_dispatch",
        version="1",
        scheduled_at=scheduled_at,
        trace_id="trace-1",
        payload={"publication_id": "publication-1"},
    )
    store.enqueue(
        job_id="job-duplicate",
        idempotency_key="same-key",
        job_type="daily_dispatch",
        version="1",
        scheduled_at=scheduled_at,
        trace_id="trace-2",
        payload={"publication_id": "publication-2"},
    )

    claimed = store.claim(owner="worker-1")
    assert claimed == {"id": "job-1", "payload": {"publication_id": "publication-1"}}
    assert store.claim(owner="worker-2") is None
    store.complete("job-1")
    assert store.get("job-1")["status"] == "SUCCEEDED"


def test_job_store_recovers_expired_lease(tmp_path) -> None:
    store = JobStore(tmp_path / "growth.db")
    scheduled_at = (datetime.now() - timedelta(seconds=1)).isoformat()
    store.enqueue(
        job_id="job-lease",
        idempotency_key="lease-key",
        job_type="trend_scan",
        version="1",
        scheduled_at=scheduled_at,
        trace_id="trace-lease",
        payload={"x": 1},
    )
    assert store.claim(owner="worker-1", lease_seconds=-1)["id"] == "job-lease"
    assert store.recover_expired_leases() == 1
    assert store.claim(owner="worker-2")["id"] == "job-lease"


def test_budget_ledger_reserve_commit_release_totals(tmp_path) -> None:
    ledger = BudgetLedger(tmp_path / "growth.db")
    ledger.reserve("run-1", 1000)
    ledger.commit("run-1", 700)
    ledger.release("run-1", 300)
    assert ledger.totals() == {"RESERVE": 1000, "COMMIT": 700, "RELEASE": 300, "OUTSTANDING": 0}


def test_budget_ledger_rejects_negative_amount(tmp_path) -> None:
    ledger = BudgetLedger(tmp_path / "growth.db")
    try:
        ledger.reserve("bad", -1)
    except ValueError as exc:
        assert "non-negative" in str(exc)
    else:
        raise AssertionError("negative budget event should fail")


def test_scheduler_uses_ict_0900() -> None:
    scheduled = next_dispatch_at(datetime(2026, 8, 4).date())
    assert scheduled == "2026-08-04T09:00:00+07:00"
