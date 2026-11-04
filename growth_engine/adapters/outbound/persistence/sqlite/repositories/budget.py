from __future__ import annotations

import re

from growth_engine.domain.ops.budget import budget_allows

from ._base import SqliteRepository


_PERIOD_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class BudgetRepository(SqliteRepository):
    """Atomic adapter for GC2 paid-call reservations on the caller's UoW connection."""

    def reserve(
        self,
        *,
        call_id: str,
        business_key: str,
        period_key: str,
        currency: str,
        provider: str,
        operation: str,
        amount_minor: int,
        cap_minor: int,
        created_at_ms: int,
    ) -> bool:
        self._require_write_transaction()
        if not all(value.strip() for value in (call_id, business_key, currency, provider, operation)):
            raise ValueError("paid-call identity, currency, provider and operation are required")
        if not _PERIOD_RE.fullmatch(period_key):
            raise ValueError("period_key must use YYYY-MM")
        if type(amount_minor) is not int or amount_minor < 0:
            raise ValueError("amount_minor must be a non-negative integer")
        if type(cap_minor) is not int or cap_minor < 0 or type(created_at_ms) is not int:
            raise ValueError("cap_minor and created_at_ms must be non-negative/integer values")

        existing = self.connection.execute(
            "SELECT id FROM paid_calls WHERE business_key=?", (business_key,)
        ).fetchone()
        if existing is not None:
            return False

        totals = self.connection.execute(
            """SELECT
                 COALESCE(SUM(CASE WHEN state='RESERVED' THEN reserved_minor ELSE 0 END), 0) AS reserved,
                 COALESCE(SUM(CASE WHEN state='UNKNOWN' THEN reserved_minor ELSE 0 END), 0) AS unknown,
                 COALESCE(SUM(CASE WHEN state='SETTLED'
                                   THEN COALESCE(actual_minor, reserved_minor) ELSE 0 END), 0) AS settled
               FROM paid_calls
               WHERE period_key=? AND currency=?
                 AND state IN ('RESERVED','UNKNOWN','SETTLED')""",
            (period_key, currency),
        ).fetchone()
        if not budget_allows(
            cap=cap_minor,
            reserved=int(totals["reserved"]),
            unknown=int(totals["unknown"]),
            settled=int(totals["settled"]),
            amount=amount_minor,
        ):
            return False

        self.connection.execute(
            """INSERT INTO paid_calls
               (id, business_key, period_key, currency, provider, operation, state,
                reserved_minor, actual_minor, external_job_id, created_at, settled_at)
               VALUES (?, ?, ?, ?, ?, ?, 'RESERVED', ?, NULL, NULL, ?, NULL)""",
            (
                call_id,
                business_key,
                period_key,
                currency,
                provider,
                operation,
                amount_minor,
                created_at_ms,
            ),
        )
        return True

    def settle(self, business_key: str, *, actual_minor: int | None, settled_at_ms: int) -> bool:
        self._require_write_transaction()
        if actual_minor is not None and (type(actual_minor) is not int or actual_minor < 0):
            raise ValueError("actual_minor must be a non-negative integer or None")
        if type(settled_at_ms) is not int:
            raise ValueError("settled_at_ms must be an integer")
        cursor = self.connection.execute(
            """UPDATE paid_calls SET state='SETTLED', actual_minor=?, settled_at=?
               WHERE business_key=? AND state='RESERVED'""",
            (actual_minor, settled_at_ms, business_key),
        )
        if cursor.rowcount == 1:
            return True
        row = self.connection.execute(
            "SELECT state, actual_minor, settled_at FROM paid_calls WHERE business_key=?",
            (business_key,),
        ).fetchone()
        return bool(
            row is not None
            and row["state"] == "SETTLED"
            and row["actual_minor"] == actual_minor
            and row["settled_at"] == settled_at_ms
        )

    def mark_unknown(self, business_key: str, *, external_job_id: str | None = None) -> bool:
        self._require_write_transaction()
        cursor = self.connection.execute(
            """UPDATE paid_calls SET state='UNKNOWN', external_job_id=?
               WHERE business_key=? AND state='RESERVED'""",
            (external_job_id, business_key),
        )
        if cursor.rowcount == 1:
            return True
        row = self.connection.execute(
            "SELECT state, external_job_id FROM paid_calls WHERE business_key=?",
            (business_key,),
        ).fetchone()
        return bool(row is not None and row["state"] == "UNKNOWN" and row["external_job_id"] == external_job_id)

    def release(self, business_key: str, *, settled_at_ms: int) -> bool:
        """Release only a call known not to have reached a paid provider."""
        self._require_write_transaction()
        if type(settled_at_ms) is not int:
            raise ValueError("settled_at_ms must be an integer")
        cursor = self.connection.execute(
            """UPDATE paid_calls SET state='RELEASED', settled_at=?
               WHERE business_key=? AND state='RESERVED'""",
            (settled_at_ms, business_key),
        )
        return cursor.rowcount == 1

    def get(self, business_key: str):
        row = self.connection.execute(
            """SELECT id, business_key, period_key, currency, provider, operation, state,
                      reserved_minor, actual_minor, external_job_id, created_at, settled_at
               FROM paid_calls WHERE business_key=?""",
            (business_key,),
        ).fetchone()
        return None if row is None else dict(row)

    def _require_write_transaction(self) -> None:
        if not self.connection.in_transaction:
            raise RuntimeError("budget writes require an active BEGIN IMMEDIATE transaction")
