from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


class JobStore:
    def __init__(self, db_path: Path = Path("data/projects/venho_hotel/growth/growth.db")) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.db_path)
        db.execute("PRAGMA busy_timeout = 5000")
        return db

    def _init(self) -> None:
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                  id TEXT PRIMARY KEY,
                  idempotency_key TEXT UNIQUE NOT NULL,
                  job_type TEXT NOT NULL,
                  version TEXT NOT NULL,
                  status TEXT NOT NULL,
                  attempt INTEGER NOT NULL,
                  max_attempt INTEGER NOT NULL,
                  lease_owner TEXT,
                  lease_expiry TEXT,
                  scheduled_at TEXT NOT NULL,
                  trace_id TEXT NOT NULL,
                  payload TEXT NOT NULL,
                  last_error TEXT,
                  last_heartbeat_at TEXT
                )
                """
            )
            columns = {row[1] for row in db.execute("PRAGMA table_info(jobs)").fetchall()}
            if "last_heartbeat_at" not in columns:
                db.execute("ALTER TABLE jobs ADD COLUMN last_heartbeat_at TEXT")

    def enqueue(self, *, job_id: str, idempotency_key: str, job_type: str, version: str, scheduled_at: str, trace_id: str, payload: dict[str, Any], max_attempt: int = 3) -> None:
        with self._connect() as db:
            db.execute(
                """
                INSERT OR IGNORE INTO jobs (
                  id, idempotency_key, job_type, version, status, attempt, max_attempt,
                  lease_owner, lease_expiry, scheduled_at, trace_id, payload, last_error, last_heartbeat_at
                ) VALUES (?, ?, ?, ?, 'READY', 0, ?, NULL, NULL, ?, ?, ?, NULL, NULL)
                """,
                (job_id, idempotency_key, job_type, version, max_attempt, scheduled_at, trace_id, json.dumps(payload)),
            )

    def claim(self, *, owner: str, lease_seconds: int = 300) -> dict[str, Any] | None:
        now = datetime.now()
        lease_expiry = (now + timedelta(seconds=lease_seconds)).isoformat()
        with self._connect() as db:
            # Single atomic UPDATE (not SELECT-then-UPDATE) so two concurrent
            # workers can never both claim the same READY job.
            row = db.execute(
                """
                UPDATE jobs SET status='RUNNING', lease_owner=?, lease_expiry=?, attempt=attempt+1, last_heartbeat_at=?
                WHERE id = (
                    SELECT id FROM jobs WHERE status='READY' AND scheduled_at <= ?
                    ORDER BY scheduled_at LIMIT 1
                ) AND status='READY'
                RETURNING id, payload
                """,
                (owner, lease_expiry, now.isoformat(), now.isoformat()),
            ).fetchone()
            if not row:
                return None
            return {"id": row[0], "payload": json.loads(row[1])}

    def heartbeat(self, job_id: str, *, owner: str, lease_seconds: int = 300) -> bool:
        now = datetime.now()
        lease_expiry = (now + timedelta(seconds=lease_seconds)).isoformat()
        with self._connect() as db:
            cursor = db.execute(
                """
                UPDATE jobs SET lease_expiry=?, last_heartbeat_at=?
                WHERE id=? AND status='RUNNING' AND lease_owner=?
                """,
                (lease_expiry, now.isoformat(), job_id, owner),
            )
            return cursor.rowcount == 1

    def recover_expired_leases(self) -> int:
        now = datetime.now().isoformat()
        with self._connect() as db:
            cursor = db.execute(
                "UPDATE jobs SET status='READY', lease_owner=NULL, lease_expiry=NULL WHERE status='RUNNING' AND lease_expiry <= ?",
                (now,),
            )
            return int(cursor.rowcount)

    def requeue_retryable_failures(self, retry_delays_seconds: dict[int, int] | None = None) -> int:
        retry_delays_seconds = retry_delays_seconds or {1: 60, 2: 300, 3: 900}
        now = datetime.now()
        with self._connect() as db:
            rows = db.execute("SELECT id, attempt FROM jobs WHERE status='RETRYABLE_FAILED' AND attempt < max_attempt").fetchall()
            for job_id, attempt in rows:
                delay = retry_delays_seconds.get(int(attempt), retry_delays_seconds.get(max(retry_delays_seconds), 900))
                db.execute(
                    "UPDATE jobs SET status='READY', scheduled_at=?, lease_owner=NULL, lease_expiry=NULL WHERE id=?",
                    ((now + timedelta(seconds=delay)).isoformat(), job_id),
                )
            return len(rows)

    def complete(self, job_id: str) -> None:
        with self._connect() as db:
            db.execute("UPDATE jobs SET status='SUCCEEDED', lease_owner=NULL, lease_expiry=NULL WHERE id=?", (job_id,))

    def fail(self, job_id: str, error: str) -> None:
        with self._connect() as db:
            db.execute(
                "UPDATE jobs SET status=CASE WHEN attempt < max_attempt THEN 'RETRYABLE_FAILED' ELSE 'TERMINAL_FAILED' END, last_error=?, lease_owner=NULL, lease_expiry=NULL WHERE id=?",
                (error[:500], job_id),
            )

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT id, idempotency_key, job_type, version, status, attempt, max_attempt, lease_owner, lease_expiry, scheduled_at, trace_id, payload, last_error, last_heartbeat_at FROM jobs WHERE id=?",
                (job_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "idempotency_key": row[1],
            "job_type": row[2],
            "version": row[3],
            "status": row[4],
            "attempt": row[5],
            "max_attempt": row[6],
            "lease_owner": row[7],
            "lease_expiry": row[8],
            "scheduled_at": row[9],
            "trace_id": row[10],
            "payload": json.loads(row[11]),
            "last_error": row[12],
            "last_heartbeat_at": row[13],
        }

    def count_by_idempotency_key(self, idempotency_key: str) -> int:
        with self._connect() as db:
            row = db.execute("SELECT COUNT(*) FROM jobs WHERE idempotency_key=?", (idempotency_key,)).fetchone()
            return int(row[0])
