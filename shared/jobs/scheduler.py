from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from shared.jobs.job_store import JobStore


def next_dispatch_at(day: date, timezone: str = "Asia/Ho_Chi_Minh") -> str:
    return datetime.combine(day, time(9, 0), tzinfo=ZoneInfo(timezone)).isoformat()


def enqueue_idempotent_dispatch(
    store: JobStore,
    *,
    publication_id: str,
    scheduled_at: str,
    trace_id: str,
    version: str = "1",
) -> str:
    job_id = f"dispatch-{publication_id}-{scheduled_at}"
    idempotency_key = f"daily_dispatch:{publication_id}:{scheduled_at}"
    store.enqueue(
        job_id=job_id,
        idempotency_key=idempotency_key,
        job_type="daily_dispatch",
        version=version,
        scheduled_at=scheduled_at,
        trace_id=trace_id,
        payload={"publication_id": publication_id},
    )
    return idempotency_key


def lateness_alert(scheduled_at: str, *, now: datetime | None = None, grace_minutes: int = 10) -> dict:
    scheduled = datetime.fromisoformat(scheduled_at)
    current = now or datetime.now(tz=scheduled.tzinfo)
    late_by = current - scheduled
    is_late = late_by > timedelta(minutes=grace_minutes)
    return {
        "alert": "LATE_RUN" if is_late else None,
        "scheduled_at": scheduled_at,
        "late_by_seconds": max(int(late_by.total_seconds()), 0),
        "grace_minutes": grace_minutes,
    }
