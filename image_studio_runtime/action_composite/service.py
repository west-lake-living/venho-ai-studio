from __future__ import annotations

import threading
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, Optional

from pydantic import BaseModel

from .audit_store import AuditStore
from .models import ActionCompositeJob
from .orchestration import AuditTrail, IdempotencyStore, IterationRecord


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class JobEnvelope(BaseModel):
    job: ActionCompositeJob
    status: JobStatus = JobStatus.QUEUED
    result: Optional[dict] = None
    error: Optional[str] = None
    audit_path: Optional[str] = None
    idempotency_key: str


class ActionCompositeService:
    """Application boundary for API/worker/CLI callers.

    Callers may be concurrent (an HTTP handler and a worker share one instance),
    so job bookkeeping is guarded by a lock while the actual execution runs
    outside it — a restoration pass takes minutes and must not block submits.
    """

    def __init__(self, audit_root: str | Path) -> None:
        self.audit_store = AuditStore(audit_root)
        self.idempotency = IdempotencyStore()
        self.jobs: Dict[str, JobEnvelope] = {}
        self._cancelled: set[str] = set()
        self._lock = threading.RLock()

    def submit(self, job: ActionCompositeJob, *, request_payload: bytes = b"") -> JobEnvelope:
        key = self.idempotency.key(job.job_id, request_payload)
        with self._lock:
            existing = self.jobs.get(job.job_id)
            if existing is not None:
                if existing.idempotency_key != key:
                    raise ValueError(
                        f"Job {job.job_id} already exists with a different request payload; "
                        "use a new job_id instead of overwriting an in-flight job")
                return existing
            envelope = JobEnvelope(job=job, idempotency_key=key)
            # A completed run recorded by an earlier service instance (or a
            # replayed request) must not be executed a second time.
            replayed = self.idempotency.get(key)
            if isinstance(replayed, dict):
                envelope.status = JobStatus.COMPLETED
                envelope.result = replayed
            self.jobs[job.job_id] = envelope
            return envelope

    def cancel(self, job_id: str) -> JobEnvelope:
        with self._lock:
            envelope = self._require(job_id)
            self._cancelled.add(job_id)
            if envelope.status in {JobStatus.QUEUED, JobStatus.RUNNING}:
                envelope.status = JobStatus.CANCELLED
            return envelope

    def run(self, job_id: str, execute: Callable[[ActionCompositeJob], object]) -> JobEnvelope:
        with self._lock:
            envelope = self._require(job_id)
            if envelope.status == JobStatus.COMPLETED:
                return envelope
            if envelope.status == JobStatus.RUNNING:
                raise RuntimeError(f"Action Composite job {job_id} is already running")
            if job_id in self._cancelled:
                envelope.status = JobStatus.CANCELLED
                return envelope
            envelope.status = JobStatus.RUNNING
            trail = self._open_trail(job_id)
            trail.append(self._record(trail, envelope, state="RUNNING"))

        try:
            result = execute(envelope.job)
        except Exception as exc:
            with self._lock:
                envelope.status = JobStatus.FAILED
                envelope.error = str(exc)
                trail.append(self._record(trail, envelope, state="FAILED", parameters={"error": str(exc)}))
                envelope.audit_path = str(self.audit_store.save(trail))
            return envelope

        with self._lock:
            if job_id in self._cancelled:
                envelope.status = JobStatus.CANCELLED
            else:
                envelope.status = JobStatus.COMPLETED
                envelope.result = _as_result(result)
                result_parameters = {}
                if isinstance(envelope.result, dict):
                    result_parameters = dict(envelope.result.get("metadata") or {})
                trail.append(self._record(trail, envelope, state="FINALIZE", parameters=result_parameters))
                self.idempotency.put(envelope.idempotency_key, envelope.result)
            envelope.audit_path = str(self.audit_store.save(trail))
            return envelope

    def resume(self, job_id: str, execute: Callable[[ActionCompositeJob], object]) -> JobEnvelope:
        with self._lock:
            envelope = self._require(job_id)
            if envelope.status not in {JobStatus.FAILED, JobStatus.CANCELLED}:
                return envelope
            self._cancelled.discard(job_id)
            envelope.status = JobStatus.QUEUED
        return self.run(job_id, execute)

    def _open_trail(self, job_id: str) -> AuditTrail:
        """Continue the existing trail so a resume keeps the failed attempt."""
        try:
            return self.audit_store.load(job_id)
        except (FileNotFoundError, ValueError):
            return AuditTrail(job_id=job_id)

    @staticmethod
    def _record(trail: AuditTrail, envelope: JobEnvelope, *, state: str,
                parameters: Optional[dict] = None) -> IterationRecord:
        latest = trail.latest
        return IterationRecord(iteration=(latest.iteration + 1) if latest else 0,
                               provider=envelope.job.provider,
                               workflow_version=envelope.job.workflow_version,
                               state=state, parameters=parameters or {})

    def _require(self, job_id: str) -> JobEnvelope:
        if job_id not in self.jobs:
            raise KeyError(f"Unknown Action Composite job: {job_id}")
        return self.jobs[job_id]


def _as_result(result: object) -> dict:
    if hasattr(result, "model_dump"):
        return result.model_dump()
    if isinstance(result, dict):
        return result
    return {"value": result}
