from __future__ import annotations

import sqlite3
import time
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from typing import Any

from growth_engine.adapters.outbound.persistence.sqlite.repositories import (
    AuditRepository,
    CandidateRepository,
    ChannelRepository,
    CommandRepository,
    ControlsRepository,
    DeliveryRepository,
    ExecutionRepository,
    IncidentRepository,
    IdempotencyRepository,
    JobRepository,
    MediaRepository,
    MetricRepository,
    PackageRepository,
    QcRepository,
    ReceiptRepository,
    SlotRepository,
)


class DatabaseBusy(RuntimeError):
    code = "ERR_GC2_DB_BUSY"
    status_code = 503


class ConcurrencyConflict(RuntimeError):
    code = "ERR_GC2_STATE_CONFLICT"
    status_code = 409


_CAS_FIELDS: dict[str, frozenset[str]] = {
    "slots": frozenset(
        {
            "local_date",
            "local_time",
            "timezone",
            "lane",
            "cadence_version",
            "scheduled_at",
            "deadline_at",
            "cancelled_at",
            "cancel_reason",
        }
    ),
    "deliveries": frozenset(
        {
            "current_revision_id",
            "active_approval_id",
            "state",
            "active",
            "blocked_reason",
            "platform_post_id",
            "permalink",
            "reported_at",
            "published_at",
            "verified_at",
            "verification_quality",
            "platform_visibility",
            "updated_at",
        }
    ),
    "research_candidates": frozenset(
        {
            "event_key",
            "event_start_at",
            "event_end_at",
            "expires_at",
            "payload_json",
            "state",
        }
    ),
}


class SqliteUnitOfWork:
    """Opens one SQLite connection per transaction and binds repositories to it."""

    def __init__(
        self,
        connection_factory: Callable[[], sqlite3.Connection],
        *,
        busy_retries: int = 5,
        sleep: Callable[[float], None] = time.sleep,
        _connection: sqlite3.Connection | None = None,
        _read_only: bool = False,
    ) -> None:
        if type(busy_retries) is not int or busy_retries < 0:
            raise ValueError("busy_retries must be a non-negative integer")
        self._connection_factory = connection_factory
        self._busy_retries = busy_retries
        self._sleep = sleep
        self._connection = _connection
        self._read_only = _read_only
        if _connection is not None:
            self._bind_repositories(_connection)

    @property
    def connection(self) -> sqlite3.Connection:
        if self._connection is None:
            raise RuntimeError("repositories are only available inside a UoW context")
        return self._connection

    @contextmanager
    def begin_immediate(self) -> Iterator[SqliteUnitOfWork]:
        connection = self._connection_factory()
        try:
            self._begin_with_retry(connection)
        except BaseException:
            connection.close()
            raise
        session = self._session(connection, read_only=False)
        try:
            yield session
        except BaseException:
            if connection.in_transaction:
                connection.rollback()
            raise
        else:
            if connection.in_transaction:
                connection.commit()
        finally:
            connection.close()

    @contextmanager
    def read_only(self) -> Iterator[SqliteUnitOfWork]:
        connection = self._connection_factory()
        try:
            connection.execute("PRAGMA query_only=ON")
            connection.execute("BEGIN")
        except BaseException:
            connection.close()
            raise
        session = self._session(connection, read_only=True)
        try:
            yield session
        except BaseException:
            if connection.in_transaction:
                connection.rollback()
            raise
        else:
            if connection.in_transaction:
                connection.commit()
        finally:
            connection.close()

    def cas_update(
        self,
        table: str,
        record_id: str,
        *,
        expected_row_version: int,
        fields: Mapping[str, object],
    ) -> int:
        connection = self.connection
        if self._read_only:
            raise sqlite3.OperationalError("attempt to write a readonly database")
        if not connection.in_transaction:
            raise RuntimeError("cas_update requires an active transaction")
        if type(expected_row_version) is not int or expected_row_version < 1:
            raise ValueError("expected_row_version must be a positive integer")
        allowed = _CAS_FIELDS.get(table)
        if allowed is None or not fields or any(field not in allowed for field in fields):
            raise ValueError(f"CAS update fields are not allowed for table {table!r}")
        columns = tuple(fields)
        assignments = ", ".join(f"{column}=?" for column in columns)
        values = tuple(_db_value(fields[column]) for column in columns)
        cursor = connection.execute(
            f"UPDATE {table} SET {assignments}, row_version=row_version+1 "
            "WHERE id=? AND row_version=?",
            (*values, record_id, expected_row_version),
        )
        if cursor.rowcount != 1:
            raise ConcurrencyConflict(
                f"stale {table} row {record_id!r} at version {expected_row_version}"
            )
        return expected_row_version + 1

    def _begin_with_retry(self, connection: sqlite3.Connection) -> None:
        for retry in range(self._busy_retries + 1):
            try:
                connection.execute("BEGIN IMMEDIATE")
                return
            except sqlite3.OperationalError as error:
                if not _is_busy(error):
                    raise
                if retry >= self._busy_retries:
                    raise DatabaseBusy("SQLite writer lock remained busy after retries") from error
                self._sleep(min(0.02 * (2**retry), 0.2))

    def _session(self, connection: sqlite3.Connection, *, read_only: bool) -> SqliteUnitOfWork:
        return SqliteUnitOfWork(
            self._connection_factory,
            busy_retries=self._busy_retries,
            sleep=self._sleep,
            _connection=connection,
            _read_only=read_only,
        )

    def _bind_repositories(self, connection: sqlite3.Connection) -> None:
        self.channels = ChannelRepository(connection)
        self.slots = SlotRepository(connection)
        self.packages = PackageRepository(connection)
        self.media = MediaRepository(connection)
        self.qc = QcRepository(connection)
        self.deliveries = DeliveryRepository(connection)
        self.commands = CommandRepository(connection)
        self.executions = ExecutionRepository(connection)
        self.receipts = ReceiptRepository(connection)
        self.audit = AuditRepository(connection)
        self.jobs = JobRepository(connection)
        self.incidents = IncidentRepository(connection)
        self.controls = ControlsRepository(connection)
        self.candidates = CandidateRepository(connection)
        self.metrics = MetricRepository(connection)
        self.idempotency = IdempotencyRepository(connection)


def _is_busy(error: sqlite3.OperationalError) -> bool:
    code = getattr(error, "sqlite_errorcode", None)
    base_code = None if code is None else code & 0xFF
    return base_code in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED} or any(
        message in str(error).casefold() for message in ("database is locked", "database is busy")
    )


def _db_value(value: Any) -> Any:
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value
    if isinstance(value, bool):
        return int(value)
    return value
