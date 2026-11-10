from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol, Sequence

from growth_engine.application.ports.clock import Clock
from growth_engine.application.publishing.apply_receipt import ApplyReceiptResult


class ReceiptJobStore(Protocol):
    def claim_apply_jobs(
        self, now_ms: int, *, limit: int = 20
    ) -> Sequence[tuple[str, str, str, str]]: ...

    def complete_apply_job(
        self, job_id: str, lease_token: str, *, at_ms: int, error_type: str | None = None
    ) -> bool: ...


class ReceiptApplier(Protocol):
    def execute(self, receipt_id: str, *, correlation_id: str) -> ApplyReceiptResult: ...


@dataclass(frozen=True)
class ReceiptJobsResult:
    claimed: int
    completed: int
    failed: int


class ProcessReceiptJobs:
    """Apply one batch of due receipt jobs without running any other worker tasks."""

    def __init__(self, store: ReceiptJobStore, applier: ReceiptApplier, clock: Clock) -> None:
        self._store = store
        self._applier = applier
        self._clock = clock

    def execute(self) -> ReceiptJobsResult:
        jobs = self._store.claim_apply_jobs(self._clock.now_ms())
        completed = 0
        failed = 0
        for job_id, lease_token, receipt_id, correlation_id in jobs:
            try:
                self._applier.execute(receipt_id, correlation_id=correlation_id)
            except Exception as error:
                self._store.complete_apply_job(
                    job_id,
                    lease_token,
                    at_ms=self._clock.now_ms(),
                    error_type=type(error).__name__,
                )
                logging.getLogger("growth_engine.publish").error(
                    "receipt apply failed: error_type=%s", type(error).__name__
                )
                failed += 1
            else:
                self._store.complete_apply_job(job_id, lease_token, at_ms=self._clock.now_ms())
                completed += 1
        return ReceiptJobsResult(claimed=len(jobs), completed=completed, failed=failed)
