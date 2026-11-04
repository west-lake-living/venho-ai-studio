from __future__ import annotations

from growth_engine.domain.kernel.hashing import sha256_hex
from growth_engine.domain.publishing.execution import Execution, ExecutionState
from growth_engine.domain.publishing.receipt import Receipt, ReceiptOutcome

from ._base import SqliteRepository, canonical_json, parse_json


class ExecutionRepository(SqliteRepository):
    def save(
        self,
        execution: Execution,
        *,
        principal_id: str,
        authorized_at_ms: int,
        updated_at_ms: int,
        error_class: str | None = None,
        resolved_by: str | None = None,
    ) -> None:
        external_outcome = (
            None
            if execution.platform_post_id is None
            else canonical_json({"platform_post_id": execution.platform_post_id})
        )
        self.connection.execute(
            """INSERT INTO executions
               (id, command_id, delivery_id, principal_id, state, grant_id, authorized_at,
                grant_expires_at, receipt_due_at, external_outcome, error_class, resolved_by,
                updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                execution.id,
                execution.command_id,
                execution.delivery_id,
                principal_id,
                execution.state.value,
                execution.grant_id,
                authorized_at_ms,
                execution.grant_expires_at_ms,
                execution.receipt_due_at_ms,
                external_outcome,
                error_class,
                resolved_by,
                updated_at_ms,
            ),
        )

    def get(self, execution_id: str) -> Execution | None:
        row = self.connection.execute(
            """SELECT id, delivery_id, command_id, grant_id, state, grant_expires_at,
                      receipt_due_at, external_outcome
               FROM executions WHERE id=?""",
            (execution_id,),
        ).fetchone()
        if row is None:
            return None
        external = parse_json(row["external_outcome"]) if row["external_outcome"] else {}
        return Execution(
            id=row["id"],
            delivery_id=row["delivery_id"],
            command_id=row["command_id"],
            grant_id=row["grant_id"],
            state=ExecutionState(row["state"]),
            grant_expires_at_ms=row["grant_expires_at"],
            receipt_due_at_ms=row["receipt_due_at"],
            platform_post_id=external.get("platform_post_id"),
        )


class ReceiptRepository(SqliteRepository):
    def save(
        self,
        receipt: Receipt,
        *,
        receipt_id: str,
        received_at_ms: int,
        processing_state: str,
        quarantine_reason: str | None = None,
    ) -> None:
        body = {
            "issuer": receipt.issuer,
            "event_id": receipt.event_id,
            "execution_id": receipt.execution_id,
            "grant_id": receipt.grant_id,
            "command_id": receipt.command_id,
            "delivery_id": receipt.delivery_id,
            "revision_id": receipt.revision_id,
            "channel_id": receipt.channel_id,
            "remote_account_id": receipt.remote_account_id,
            "payload_hash": receipt.payload_hash,
            "outcome": receipt.outcome.value,
            "platform_post_id": receipt.platform_post_id,
            "error_class": receipt.error_class,
        }
        body_json = canonical_json(body)
        event_hash = sha256_hex(body_json.encode("utf-8"))
        self.connection.execute(
            """INSERT INTO receipt_inbox
               (id, issuer_id, event_id, execution_id, event_hash, body_json, received_at,
                processing_state, quarantine_reason)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                receipt_id,
                receipt.issuer,
                receipt.event_id,
                receipt.execution_id,
                event_hash,
                body_json,
                received_at_ms,
                processing_state,
                quarantine_reason,
            ),
        )

    def get(self, receipt_id: str) -> Receipt | None:
        row = self.connection.execute(
            "SELECT body_json FROM receipt_inbox WHERE id=?", (receipt_id,)
        ).fetchone()
        if row is None:
            return None
        body = parse_json(row["body_json"])
        return Receipt(
            issuer=body["issuer"],
            event_id=body["event_id"],
            execution_id=body["execution_id"],
            grant_id=body["grant_id"],
            command_id=body["command_id"],
            delivery_id=body["delivery_id"],
            revision_id=body["revision_id"],
            channel_id=body["channel_id"],
            remote_account_id=body["remote_account_id"],
            payload_hash=body["payload_hash"],
            outcome=ReceiptOutcome(body["outcome"]),
            platform_post_id=body["platform_post_id"],
            error_class=body["error_class"],
        )
