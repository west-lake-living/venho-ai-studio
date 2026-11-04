from __future__ import annotations

import secrets
import sqlite3
from collections.abc import Mapping
from typing import Any


_LEASE_TABLES = {
    "outbox_commands": frozenset(
        {"id", "state", "sequence_no", "next_attempt_at", "expires_at", "lease_owner", "lease_until"}
    ),
    "jobs": frozenset(
        {"id", "kind", "lane", "business_key", "state", "run_at", "lease_owner", "lease_until"}
    ),
}
_COMPLETE_FIELDS = {
    "outbox_commands": frozenset(
        {"state", "acked_at", "next_attempt_at", "transport_attempts", "last_error", "updated_at"}
    ),
    "jobs": frozenset({"state", "attempts", "run_at", "last_error", "updated_at"}),
}


WhereValue = object | tuple[str, object]


def claim_with_lease(
    connection: sqlite3.Connection,
    table: str,
    where: Mapping[str, WhereValue],
    owner: str,
    lease_ms: int,
    *,
    now_ms: int,
) -> tuple[sqlite3.Row | tuple[Any, ...], str] | None:
    """Atomically claim a due command/job and replace any expired fencing token."""
    allowed_columns = _LEASE_TABLES.get(table)
    if allowed_columns is None:
        raise ValueError(f"leasing is not supported for table {table!r}")
    if not connection.in_transaction:
        raise RuntimeError("claim_with_lease requires an active transaction")
    if not owner.strip() or type(lease_ms) is not int or lease_ms <= 0 or type(now_ms) is not int:
        raise ValueError("owner and lease timestamps are invalid")
    where_sql, parameters = _where_clause(where, allowed_columns)
    token = secrets.token_urlsafe(32)
    claimed_state = "DELIVERING" if table == "outbox_commands" else "RUNNING"
    cursor = connection.execute(
        f"UPDATE {table} SET state=?, lease_owner=?, lease_token=?, lease_until=?, updated_at=? "
        f"WHERE {where_sql} RETURNING *",
        (claimed_state, owner, token, now_ms + lease_ms, now_ms, *parameters),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return row, token


def complete_with_lease(
    connection: sqlite3.Connection,
    table: str,
    record_id: str,
    lease_token: str,
    *,
    fields: Mapping[str, object],
) -> bool:
    """Complete a lease only if the stored fencing token still belongs to the caller."""
    allowed_fields = _COMPLETE_FIELDS.get(table)
    if allowed_fields is None:
        raise ValueError(f"leasing is not supported for table {table!r}")
    if not connection.in_transaction:
        raise RuntimeError("complete_with_lease requires an active transaction")
    if not record_id.strip() or not lease_token.strip() or not fields:
        raise ValueError("record id, lease token, and completion fields are required")
    if any(field not in allowed_fields for field in fields):
        raise ValueError(f"completion fields are not allowed for table {table!r}")
    columns = tuple(fields)
    assignments = ", ".join(f"{column}=?" for column in columns)
    cursor = connection.execute(
        f"UPDATE {table} SET {assignments}, lease_owner=NULL, lease_token=NULL, lease_until=NULL "
        "WHERE id=? AND lease_token=?",
        (*(_db_value(fields[column]) for column in columns), record_id, lease_token),
    )
    return cursor.rowcount == 1


def _where_clause(
    where: Mapping[str, WhereValue], allowed_columns: frozenset[str]
) -> tuple[str, tuple[object, ...]]:
    if not where or any(column not in allowed_columns for column in where):
        raise ValueError("lease predicates must use an allowlisted, non-empty column set")
    conditions: list[str] = []
    parameters: list[object] = []
    for column, value in where.items():
        operator = "="
        operand = value
        if isinstance(value, tuple):
            if len(value) != 2 or value[0] not in {"=", "!=", "<", "<=", ">", ">="}:
                raise ValueError(f"invalid lease predicate for {column!r}")
            operator, operand = value
        if operand is None and operator in {"=", "!="}:
            conditions.append(f"{column} IS {'NOT ' if operator == '!=' else ''}NULL")
        else:
            conditions.append(f"{column} {operator} ?")
            parameters.append(_db_value(operand))
    return " AND ".join(conditions), tuple(parameters)


def _db_value(value: Any) -> Any:
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value
    if isinstance(value, bool):
        return int(value)
    return value
