from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from growth_engine.adapters.outbound.persistence.sqlite.cas import claim_with_lease, complete_with_lease

from ._base import SqliteRepository, canonical_json, parse_json


@dataclass(frozen=True)
class JobRecord:
    id: str
    kind: str
    lane: str
    business_key: str
    payload_json: str
    state: str
    run_at_ms: int
    attempts: int = 0
    max_attempts: int = 3
    lease_owner: str | None = None
    lease_token: str | None = None
    lease_until_ms: int | None = None
    last_error: str | None = None
    created_at_ms: int = 0
    updated_at_ms: int = 0


class JobRepository(SqliteRepository):
    def save(self, job: JobRecord) -> None:
        self.connection.execute(
            """INSERT INTO jobs
               (id, kind, lane, business_key, payload_json, state, attempts, max_attempts,
                run_at, lease_owner, lease_token, lease_until, last_error, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                job.id,
                job.kind,
                job.lane,
                job.business_key,
                canonical_json(parse_json(job.payload_json)),
                job.state,
                job.attempts,
                job.max_attempts,
                job.run_at_ms,
                job.lease_owner,
                job.lease_token,
                job.lease_until_ms,
                job.last_error,
                job.created_at_ms,
                job.updated_at_ms,
            ),
        )

    def get(self, job_id: str) -> JobRecord | None:
        row = self.connection.execute(
            """SELECT id, kind, lane, business_key, payload_json, state, attempts, max_attempts,
                      run_at, lease_owner, lease_token, lease_until, last_error, created_at, updated_at
               FROM jobs WHERE id=?""",
            (job_id,),
        ).fetchone()
        if row is None:
            return None
        return JobRecord(
            id=row["id"],
            kind=row["kind"],
            lane=row["lane"],
            business_key=row["business_key"],
            payload_json=row["payload_json"],
            state=row["state"],
            attempts=row["attempts"],
            max_attempts=row["max_attempts"],
            run_at_ms=row["run_at"],
            lease_owner=row["lease_owner"],
            lease_token=row["lease_token"],
            lease_until_ms=row["lease_until"],
            last_error=row["last_error"],
            created_at_ms=row["created_at"],
            updated_at_ms=row["updated_at"],
        )

    def claim_with_lease(
        self,
        where: Mapping[str, object],
        *,
        owner: str,
        lease_ms: int,
        now_ms: int,
    ):
        return claim_with_lease(self.connection, "jobs", where, owner, lease_ms, now_ms=now_ms)

    def complete(
        self,
        job_id: str,
        lease_token: str,
        *,
        updated_at_ms: int,
        state: str = "SUCCEEDED",
        last_error: str | None = None,
    ) -> bool:
        if state not in {"SUCCEEDED", "FAILED", "DEAD", "CANCELLED", "UNKNOWN"}:
            raise ValueError("job completion state is invalid")
        return complete_with_lease(
            self.connection,
            "jobs",
            job_id,
            lease_token,
            fields={"state": state, "last_error": last_error, "updated_at": updated_at_ms},
        )
