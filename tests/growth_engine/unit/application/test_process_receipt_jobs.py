from __future__ import annotations

from types import SimpleNamespace

from growth_engine.application.publishing.process_receipt_jobs import ProcessReceiptJobs


class FakeStore:
    def __init__(self, jobs):
        self.jobs = jobs
        self.completed = []

    def claim_apply_jobs(self, now_ms, *, limit=20):
        assert now_ms == 1234
        assert limit == 20
        return self.jobs

    def complete_apply_job(self, job_id, lease_token, *, at_ms, error_type=None):
        self.completed.append((job_id, lease_token, at_ms, error_type))
        return True


class FakeClock:
    def now_ms(self):
        return 1234


def test_process_receipt_jobs_applies_claimed_receipts_once():
    store = FakeStore([("job-1", "lease-1", "receipt-1", "corr-1")])
    applied = []
    processor = ProcessReceiptJobs(
        store,
        SimpleNamespace(execute=lambda receipt_id, *, correlation_id: applied.append((receipt_id, correlation_id))),
        FakeClock(),
    )

    result = processor.execute()

    assert (result.claimed, result.completed, result.failed) == (1, 1, 0)
    assert applied == [("receipt-1", "corr-1")]
    assert store.completed == [("job-1", "lease-1", 1234, None)]


def test_process_receipt_jobs_reschedules_failed_receipt_without_leaking_error():
    store = FakeStore([("job-1", "lease-1", "receipt-1", "corr-1")])

    def fail(_receipt_id, *, correlation_id):
        raise RuntimeError("sensitive payload must not be stored")

    processor = ProcessReceiptJobs(store, SimpleNamespace(execute=fail), FakeClock())
    result = processor.execute()

    assert (result.claimed, result.completed, result.failed) == (1, 0, 1)
    assert store.completed == [("job-1", "lease-1", 1234, "RuntimeError")]
    assert "sensitive payload" not in repr(store.completed)
