from __future__ import annotations

from growth_engine.domain.kernel.hashing import sha256_hex
from growth_engine.domain.publishing.command import CommandState, OutboxCommand
from growth_engine.domain.publishing.execution import Execution, ExecutionState
from growth_engine.domain.publishing.receipt import Receipt, ReceiptOutcome

from ._base import SqliteRepository, canonical_json, parse_json


class CommandRepository(SqliteRepository):
    def save(
        self,
        command: OutboxCommand,
        *,
        payload_hash: str,
        dispatch_epoch: str,
        created_at_ms: int,
        updated_at_ms: int,
        last_error: str | None = None,
    ) -> None:
        """Persist the durable envelope fields; signed envelope tokens are not stored."""
        self.connection.execute(
            """INSERT INTO outbox_commands
               (id, delivery_id, revision_id, sequence_no, kind, business_key, payload_hash,
                state, dispatch_epoch, expires_at, next_attempt_at, transport_attempts,
                acked_at, lease_token, lease_until, last_error, created_at, updated_at)
               VALUES (?, ?, ?, ?, 'PUBLISH', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                command.id,
                command.delivery_id,
                command.revision_id,
                command.sequence_no,
                command.business_key,
                payload_hash,
                command.state.value,
                dispatch_epoch,
                command.expires_at_ms,
                command.next_attempt_at_ms,
                command.attempts,
                command.acked_at_ms,
                command.lease_token,
                command.lease_expires_at_ms,
                last_error,
                created_at_ms,
                updated_at_ms,
            ),
        )

    def get(self, command_id: str, *, envelope_token: str) -> OutboxCommand | None:
        """Hydrate the non-persisted signed envelope token from its issuer."""
        row = self.connection.execute(
            """SELECT id, delivery_id, revision_id, sequence_no, business_key, expires_at,
                      next_attempt_at, state, transport_attempts, lease_token, lease_until, acked_at
               FROM outbox_commands WHERE id=?""",
            (command_id,),
        ).fetchone()
        if row is None:
            return None
        return OutboxCommand(
            id=row["id"],
            delivery_id=row["delivery_id"],
            revision_id=row["revision_id"],
            sequence_no=row["sequence_no"],
            business_key=row["business_key"],
            expires_at_ms=row["expires_at"],
            next_attempt_at_ms=row["next_attempt_at"],
            envelope_token=envelope_token,
            state=CommandState(row["state"]),
            attempts=row["transport_attempts"],
            lease_token=row["lease_token"],
            lease_expires_at_ms=row["lease_until"],
            acked_at_ms=row["acked_at"],
        )


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
