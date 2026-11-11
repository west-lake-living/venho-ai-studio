from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from typing import Any

from growth_engine.application.ports.uow import UnitOfWork
from growth_engine.application.publishing.apply_receipt import ReceiptApplySnapshot
from growth_engine.application.publishing.receive_receipt import (
    ReceiptInboxRecord,
    ReceiptPersistenceUnavailable,
)
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.states import DeliveryState
from growth_engine.domain.kernel.hashing import canonical_json_bytes
from growth_engine.domain.ops.incident import (
    Incident,
    IncidentSeverity,
    IncidentState,
    incident_fingerprint,
)
from growth_engine.domain.publishing.execution import Execution, ExecutionState
from growth_engine.adapters.outbound.persistence.sqlite.uow import DatabaseBusy


class SqliteReceiptStore:
    """Receive, apply, and timeout receipts inside SQLite immediate transactions."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    @contextmanager
    def begin_immediate(self) -> Iterator["SqliteReceiptTransaction"]:
        try:
            with self._uow_factory().begin_immediate() as tx:
                yield SqliteReceiptTransaction(tx)
        except (sqlite3.Error, DatabaseBusy) as error:
            raise ReceiptPersistenceUnavailable("receipt persistence is unavailable") from error

    def claim_apply_jobs(self, now_ms: int, *, limit: int = 20) -> Sequence[tuple[str, str, str, str]]:
        claimed: list[tuple[str, str, str, str]] = []
        with self._uow_factory().begin_immediate() as tx:
            rows = tx.connection.execute(
                """SELECT id, payload_json FROM jobs
                   WHERE lane='publish' AND kind='apply_receipt' AND state='PENDING' AND run_at<=?
                   ORDER BY run_at, id LIMIT ?""",
                (now_ms, limit),
            ).fetchall()
            for row in rows:
                result = tx.jobs.claim_with_lease(
                    {"id": row["id"], "state": "PENDING", "run_at": ("<=", now_ms)},
                    owner="publish-receipt-worker",
                    lease_ms=30_000,
                    now_ms=now_ms,
                )
                if result is None:
                    continue
                claimed_row, token = result
                payload = json.loads(claimed_row["payload_json"])
                receipt_id = payload.get("receipt_id")
                correlation_id = payload.get("correlation_id")
                if isinstance(receipt_id, str) and isinstance(correlation_id, str):
                    claimed.append((claimed_row["id"], token, receipt_id, correlation_id))
        return tuple(claimed)

    def complete_apply_job(
        self,
        job_id: str,
        lease_token: str,
        *,
        at_ms: int,
        error_type: str | None = None,
    ) -> bool:
        with self._uow_factory().begin_immediate() as tx:
            if error_type is None:
                return tx.jobs.complete(
                    job_id,
                    lease_token,
                    updated_at_ms=at_ms,
                    state="SUCCEEDED",
                )
            row = tx.connection.execute(
                "SELECT attempts, max_attempts FROM jobs WHERE id=? AND lease_token=?",
                (job_id, lease_token),
            ).fetchone()
            if row is None:
                return False
            attempts = int(row["attempts"]) + 1
            state = "DEAD" if attempts >= int(row["max_attempts"]) else "PENDING"
            retry_at = at_ms + min(300_000, 5_000 * (2 ** min(attempts, 6)))
            from growth_engine.adapters.outbound.persistence.sqlite.cas import complete_with_lease

            return complete_with_lease(
                tx.connection,
                "jobs",
                job_id,
                lease_token,
                fields={
                    "state": state,
                    "attempts": attempts,
                    "run_at": retry_at,
                    "last_error": f"apply_receipt:{error_type[:64]}",
                    "updated_at": at_ms,
                },
            )


class SqliteReceiptTransaction:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    @property
    def connection(self):
        return self._uow.connection

    def find_receipt(self, issuer_id: str, event_id: str) -> ReceiptInboxRecord | None:
        row = self.connection.execute(
            """SELECT id, issuer_id, event_id, event_hash, body_json, received_at,
                      processing_state, quarantine_reason
               FROM receipt_inbox WHERE issuer_id=? AND event_id=?""",
            (issuer_id, event_id),
        ).fetchone()
        return None if row is None else _receipt_record(row)

    def insert_receipt(self, record: ReceiptInboxRecord) -> None:
        self.connection.execute(
            """INSERT INTO receipt_inbox
               (id, issuer_id, event_id, event_hash, body_json, received_at,
                processing_state, quarantine_reason)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record.id,
                record.issuer_id,
                record.event_id,
                record.event_hash,
                canonical_json_bytes(dict(record.body)).decode("utf-8"),
                record.received_at_ms,
                record.processing_state,
                record.quarantine_reason,
            ),
        )

    def enqueue_apply_receipt(
        self,
        receipt_id: str,
        job_id: str,
        *,
        run_at_ms: int,
        correlation_id: str,
    ) -> None:
        from growth_engine.adapters.outbound.persistence.sqlite.repositories.jobs import JobRecord

        payload = canonical_json_bytes(
            {"receipt_id": receipt_id, "correlation_id": correlation_id}
        ).decode("utf-8")
        self._uow.jobs.save(
            JobRecord(
                id=job_id,
                kind="apply_receipt",
                lane="publish",
                business_key=f"receipt:{receipt_id}",
                payload_json=payload,
                state="PENDING",
                run_at_ms=run_at_ms,
                created_at_ms=run_at_ms,
                updated_at_ms=run_at_ms,
            )
        )

    def record_incident(self, **incident: object) -> None:
        record = _incident_from_payload(incident)
        self._uow.incidents.open_or_touch(record, details_json=_json_details(incident.get("details", {})))

    def append_audit(self, **entry: object) -> None:
        self._uow.audit.append(
            event_id=str(entry["audit_id"]),
            aggregate_type=str(entry["aggregate_type"]),
            aggregate_id=str(entry["aggregate_id"]),
            actor="growth-engine",
            action=str(entry["action"]),
            before_hash=None,
            after_hash=str(entry.get("details", {}).get("incoming_hash", "")) or None,
            details_json=_json_details(entry.get("details", {})),
            correlation_id=str(entry["correlation_id"]),
            created_at_ms=int(entry["at_ms"]),
        )

    def load_for_apply(self, receipt_id: str) -> ReceiptApplySnapshot | None:
        row = self.connection.execute(
            """SELECT i.id, i.issuer_id, i.event_id, i.event_hash, i.body_json, i.received_at,
                      i.processing_state, i.quarantine_reason,
                      e.id AS execution_id, e.command_id, e.delivery_id, e.principal_id,
                      c.revision_id, c.payload_hash, d.channel_id, ch.remote_account_id
               FROM receipt_inbox i
               LEFT JOIN executions e ON e.id=json_extract(i.body_json, '$.execution_id')
               LEFT JOIN outbox_commands c ON c.id=e.command_id
               LEFT JOIN deliveries d ON d.id=e.delivery_id
               LEFT JOIN channels ch ON ch.id=d.channel_id
               WHERE i.id=?""",
            (receipt_id,),
        ).fetchone()
        if row is None:
            return None
        record = _receipt_record(row)
        execution = self._uow.executions.get(row["execution_id"]) if row["execution_id"] else None
        delivery = self._uow.deliveries.get(row["delivery_id"]) if row["delivery_id"] else None
        return ReceiptApplySnapshot(
            record=record,
            execution=execution,
            delivery=delivery,
            command_id=row["command_id"] or str(record.body.get("command_id", "")),
            revision_id=row["revision_id"] or "",
            channel_id=row["channel_id"] or "",
            remote_page_id=row["remote_account_id"] or "",
            payload_hash=row["payload_hash"] or "",
            principal_id=row["principal_id"] or "",
        )

    def commit_apply(
        self,
        snapshot: ReceiptApplySnapshot,
        *,
        execution: Execution | None,
        delivery: Delivery | None,
        processing_state: str,
        reason: str | None,
        verify_at_ms: int | None,
        incident: dict[str, object] | None,
        audit_id: str,
        correlation_id: str,
        at_ms: int,
    ) -> bool:
        connection = self.connection
        connection.execute("SAVEPOINT apply_receipt")
        if execution is not None and delivery is not None:
            current = snapshot.execution
            if current is None:
                connection.execute("ROLLBACK TO apply_receipt")
                connection.execute("RELEASE apply_receipt")
                return False
            external = (
                None
                if execution.platform_post_id is None
                else canonical_json_bytes({"platform_post_id": execution.platform_post_id}).decode("utf-8")
            )
            body = snapshot.record.body
            error = body.get("error") if isinstance(body, dict) else None
            error_class = error.get("class") if isinstance(error, dict) else None
            execution_update = connection.execute(
                """UPDATE executions SET state=?, external_outcome=?, error_class=?, updated_at=?
                   WHERE id=? AND state=? AND command_id=? AND delivery_id=?""",
                (
                    execution.state.value,
                    external,
                    error_class,
                    at_ms,
                    execution.id,
                    current.state.value,
                    snapshot.command_id,
                    delivery.id,
                ),
            )
            delivery_update = connection.execute(
                """UPDATE deliveries SET state=?, permalink=?, platform_post_id=?, reported_at=?,
                          row_version=row_version+1, updated_at=?
                   WHERE id=? AND row_version=? AND state=? AND channel_id=?""",
                (
                    delivery.state.value,
                    delivery.permalink,
                    execution.platform_post_id,
                    at_ms if delivery.state is DeliveryState.REPORTED_PUBLISHED else None,
                    at_ms,
                    delivery.id,
                    snapshot.delivery.row_version if snapshot.delivery else -1,
                    snapshot.delivery.state.value if snapshot.delivery else "",
                    snapshot.channel_id,
                ),
            )
            if execution_update.rowcount != 1 or delivery_update.rowcount != 1:
                connection.execute("ROLLBACK TO apply_receipt")
                connection.execute("RELEASE apply_receipt")
                return False

        # AUTHORIZED is the terminal outbox/transport state: once the admission
        # CAS wins, the command must never be delivered again. Receipt lifecycle
        # is tracked independently by executions and deliveries.
        updated_receipt = connection.execute(
            """UPDATE receipt_inbox SET processing_state=?, quarantine_reason=?, applied_at=?
               WHERE id=? AND processing_state='RECEIVED'""",
            (processing_state, reason, at_ms, snapshot.record.id),
        )
        if updated_receipt.rowcount != 1:
            connection.execute("ROLLBACK TO apply_receipt")
            connection.execute("RELEASE apply_receipt")
            return False
        if incident is not None:
            self.record_incident(**incident)
        if verify_at_ms is not None and delivery is not None and execution is not None:
            self._enqueue_verify(delivery.id, execution.id, verify_at_ms, at_ms)
        self._append_receipt_audit(
            audit_id,
            snapshot.record.id,
            "receipt.applied" if processing_state == "APPLIED" else f"receipt.{processing_state.lower()}",
            {"processing_state": processing_state, "reason": reason},
            correlation_id,
            at_ms,
        )
        connection.execute("RELEASE apply_receipt")
        return True

    def list_due_receipt_timeouts(self, now_ms: int, limit: int) -> Sequence[ReceiptApplySnapshot]:
        rows = self.connection.execute(
            """SELECT e.id
               FROM executions e JOIN deliveries d ON d.id=e.delivery_id
               WHERE e.state='AUTHORIZED' AND d.state='EXECUTING' AND e.receipt_due_at<?
                 AND NOT EXISTS (
                   SELECT 1 FROM receipt_inbox i
                   WHERE json_extract(i.body_json, '$.execution_id')=e.id
                     AND i.processing_state='RECEIVED'
                 )
               ORDER BY e.receipt_due_at, e.id LIMIT ?""",
            (now_ms, limit),
        ).fetchall()
        candidates: list[ReceiptApplySnapshot] = []
        for row in rows:
            candidate = self._snapshot_for_execution(row["id"])
            if candidate is not None:
                candidates.append(candidate)
        return tuple(candidates)

    def commit_timeout(
        self,
        candidate: ReceiptApplySnapshot,
        *,
        execution: Execution,
        delivery: Delivery,
        incident: dict[str, object],
        audit_id: str,
        correlation_id: str,
        at_ms: int,
    ) -> bool:
        connection = self.connection
        connection.execute("SAVEPOINT timeout_receipt")
        execution_update = connection.execute(
            "UPDATE executions SET state='UNKNOWN', updated_at=? WHERE id=? AND state='AUTHORIZED'",
            (at_ms, execution.id),
        )
        delivery_update = connection.execute(
            """UPDATE deliveries SET state='UNKNOWN', row_version=row_version+1, updated_at=?
               WHERE id=? AND row_version=? AND state='EXECUTING' AND channel_id=?""",
            (
                at_ms,
                delivery.id,
                candidate.delivery.row_version if candidate.delivery else -1,
                candidate.channel_id,
            ),
        )
        if execution_update.rowcount != 1 or delivery_update.rowcount != 1:
            connection.execute("ROLLBACK TO timeout_receipt")
            connection.execute("RELEASE timeout_receipt")
            return False
        self.record_incident(**incident)
        self._append_receipt_audit(
            audit_id,
            candidate.record.id,
            "receipt.timeout_unknown",
            {"execution_id": execution.id, "receipt_due_at_ms": execution.receipt_due_at_ms},
            correlation_id,
            at_ms,
        )
        connection.execute("RELEASE timeout_receipt")
        return True

    def _snapshot_for_execution(self, execution_id: str) -> ReceiptApplySnapshot | None:
        row = self.connection.execute(
            """SELECT e.id AS execution_id, e.command_id, e.delivery_id, e.principal_id,
                      c.revision_id, c.payload_hash, d.channel_id, ch.remote_account_id,
                      e.authorized_at, e.receipt_due_at
               FROM executions e JOIN outbox_commands c ON c.id=e.command_id
               JOIN deliveries d ON d.id=e.delivery_id
               JOIN channels ch ON ch.id=d.channel_id WHERE e.id=?""",
            (execution_id,),
        ).fetchone()
        if row is None:
            return None
        execution = self._uow.executions.get(execution_id)
        delivery = self._uow.deliveries.get(row["delivery_id"])
        if execution is None or delivery is None:
            return None
        placeholder = ReceiptInboxRecord(
            id=f"timeout:{execution_id}",
            issuer_id=row["principal_id"],
            event_id="",
            event_hash="",
            body={},
            received_at_ms=row["authorized_at"],
            processing_state="TIMEOUT",
        )
        return ReceiptApplySnapshot(
            record=placeholder,
            execution=execution,
            delivery=delivery,
            command_id=row["command_id"],
            revision_id=row["revision_id"],
            channel_id=row["channel_id"],
            remote_page_id=row["remote_account_id"],
            payload_hash=row["payload_hash"],
            principal_id=row["principal_id"],
        )

    def _enqueue_verify(self, delivery_id: str, execution_id: str, run_at_ms: int, created_at_ms: int) -> None:
        from growth_engine.adapters.outbound.persistence.sqlite.repositories.jobs import JobRecord

        job_id = f"verify:{delivery_id}:{execution_id}"
        self._uow.jobs.save(
            JobRecord(
                id=job_id,
                kind="verify_publication",
                lane="publish",
                business_key=f"verify:{delivery_id}:{execution_id}",
                payload_json=canonical_json_bytes(
                    {"delivery_id": delivery_id, "execution_id": execution_id}
                ).decode("utf-8"),
                state="PENDING",
                run_at_ms=run_at_ms,
                created_at_ms=created_at_ms,
                updated_at_ms=created_at_ms,
            )
        )

    def _append_receipt_audit(
        self,
        audit_id: str,
        receipt_id: str,
        action: str,
        details: dict[str, object],
        correlation_id: str,
        at_ms: int,
    ) -> None:
        self._uow.audit.append(
            event_id=audit_id,
            aggregate_type="receipt",
            aggregate_id=receipt_id,
            actor="growth-engine",
            action=action,
            before_hash=None,
            after_hash=None,
            details_json=canonical_json_bytes(details).decode("utf-8"),
            correlation_id=correlation_id,
            created_at_ms=at_ms,
        )


def _receipt_record(row) -> ReceiptInboxRecord:
    return ReceiptInboxRecord(
        id=row["id"],
        issuer_id=row["issuer_id"],
        event_id=row["event_id"],
        event_hash=row["event_hash"],
        body=json.loads(row["body_json"]),
        received_at_ms=row["received_at"],
        processing_state=row["processing_state"],
        quarantine_reason=row["quarantine_reason"],
    )


def _incident_from_payload(values: dict[str, object]) -> Incident:
    incident_type = str(values["incident_type"])
    channel_id = values.get("channel_id")
    ref = str(values["ref"])
    at_ms = int(values["at_ms"])
    severity = IncidentSeverity(str(values["severity"]))
    return Incident(
        id=str(values["incident_id"]),
        type=incident_type,
        fingerprint=incident_fingerprint(incident_type, channel_id if isinstance(channel_id, str) else None, ref),
        channel_id=channel_id if isinstance(channel_id, str) else None,
        ref=ref,
        severity=severity,
        state=IncidentState.OPEN,
        first_seen_at_ms=at_ms,
        last_seen_at_ms=at_ms,
    )


def _json_details(value: object) -> str:
    return canonical_json_bytes(value if isinstance(value, dict) else {}).decode("utf-8")
