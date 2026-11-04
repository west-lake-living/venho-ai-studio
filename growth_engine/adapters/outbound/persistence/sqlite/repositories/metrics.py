from __future__ import annotations

import secrets
from collections.abc import Sequence

from growth_engine.domain.analytics.metric import MetricObservation

from ._base import SqliteRepository, canonical_json


class MetricRepository(SqliteRepository):
    """Append metric observations and fence each checkpoint collection through jobs."""

    def claim_collection(
        self, *, job_id: str, business_key: str, now_ms: int, lease_ms: int
    ) -> tuple[str, str] | None:
        if not self.connection.in_transaction:
            raise RuntimeError("claim_collection requires an active transaction")
        if not job_id.strip() or not business_key.strip() or lease_ms <= 0:
            raise ValueError("metrics job key and lease must be valid")

        row = self.connection.execute(
            "SELECT id, state, attempts, max_attempts, run_at, lease_until "
            "FROM jobs WHERE kind='metrics' AND business_key=?",
            (business_key,),
        ).fetchone()
        if row is None:
            self.connection.execute(
                """INSERT INTO jobs
                   (id, kind, lane, business_key, payload_json, state, attempts, max_attempts,
                    run_at, created_at, updated_at)
                   VALUES (?, 'metrics', 'jobs', ?, ?, 'PENDING', 0, 3, ?, ?, ?)""",
                (
                    job_id,
                    business_key,
                    canonical_json({"job_key": business_key}),
                    now_ms,
                    now_ms,
                    now_ms,
                ),
            )
            row = self.connection.execute(
                "SELECT id, state, attempts, max_attempts, run_at, lease_until "
                "FROM jobs WHERE kind='metrics' AND business_key=?",
                (business_key,),
            ).fetchone()
        assert row is not None

        if row["state"] == "SUCCEEDED" or row["state"] in {"DEAD", "CANCELLED", "UNKNOWN"}:
            return None
        if row["state"] == "RUNNING":
            if row["lease_until"] is not None and row["lease_until"] > now_ms:
                return None
            if row["attempts"] >= row["max_attempts"]:
                self.connection.execute(
                    "UPDATE jobs SET state='DEAD', lease_owner=NULL, lease_token=NULL, "
                    "lease_until=NULL, updated_at=? WHERE id=?",
                    (now_ms, row["id"]),
                )
                return None
            self.connection.execute(
                "UPDATE jobs SET state='PENDING', lease_owner=NULL, lease_token=NULL, "
                "lease_until=NULL, updated_at=? WHERE id=?",
                (now_ms, row["id"]),
            )
        elif row["state"] == "FAILED":
            if row["run_at"] > now_ms:
                return None
            if row["attempts"] >= row["max_attempts"]:
                self.connection.execute(
                    "UPDATE jobs SET state='DEAD', updated_at=? WHERE id=?",
                    (now_ms, row["id"]),
                )
                return None
            self.connection.execute(
                "UPDATE jobs SET state='PENDING', updated_at=? WHERE id=?",
                (now_ms, row["id"]),
            )
        elif row["state"] != "PENDING":
            return None

        lease_token = secrets.token_urlsafe(32)
        cursor = self.connection.execute(
            """UPDATE jobs SET state='RUNNING', attempts=attempts+1,
                      lease_owner='metrics-collector', lease_token=?, lease_until=?, updated_at=?
               WHERE id=? AND state='PENDING'""",
            (lease_token, now_ms + lease_ms, now_ms, row["id"]),
        )
        if cursor.rowcount != 1:
            return None
        return str(row["id"]), lease_token

    def append(self, observations: Sequence[MetricObservation]) -> int:
        if not self.connection.in_transaction:
            raise RuntimeError("append requires an active transaction")
        inserted = 0
        for observation in observations:
            cursor = self.connection.execute(
                """INSERT OR IGNORE INTO metric_observations
                   (id, delivery_id, metric, checkpoint, observed_at, post_age_seconds, value,
                    value_state, source, api_version, period, dimensions_json, error_code)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    observation.id,
                    observation.delivery_id,
                    observation.metric,
                    observation.checkpoint.value,
                    observation.observed_at_ms,
                    observation.post_age_seconds,
                    observation.value,
                    observation.value_state.value,
                    observation.source,
                    observation.api_version,
                    observation.period,
                    canonical_json(dict(observation.dimensions)),
                    observation.error_code,
                ),
            )
            inserted += cursor.rowcount
        return inserted

    def complete_collection(
        self,
        job_id: str,
        lease_token: str,
        *,
        now_ms: int,
        failed: bool,
        retry_delay_ms: int,
    ) -> bool:
        if not self.connection.in_transaction:
            raise RuntimeError("complete_collection requires an active transaction")
        if type(failed) is not bool or retry_delay_ms < 0:
            raise ValueError("collection result and retry delay are invalid")
        row = self.connection.execute(
            "SELECT attempts, max_attempts FROM jobs WHERE id=? AND state='RUNNING' AND lease_token=?",
            (job_id, lease_token),
        ).fetchone()
        if row is None:
            return False
        state = "SUCCEEDED"
        run_at_ms = now_ms
        last_error = None
        if failed:
            state = "FAILED" if row["attempts"] < row["max_attempts"] else "DEAD"
            run_at_ms = now_ms + retry_delay_ms if state == "FAILED" else now_ms
            last_error = "METRIC_COLLECTION_ERROR"
        cursor = self.connection.execute(
            """UPDATE jobs SET state=?, run_at=?, last_error=?, updated_at=?,
                      lease_owner=NULL, lease_token=NULL, lease_until=NULL
               WHERE id=? AND state='RUNNING' AND lease_token=?""",
            (state, run_at_ms, last_error, now_ms, job_id, lease_token),
        )
        return cursor.rowcount == 1
