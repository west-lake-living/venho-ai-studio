from __future__ import annotations

from collections.abc import Mapping

from growth_engine.adapters.outbound.persistence.sqlite.cas import claim_with_lease, complete_with_lease
from growth_engine.domain.publishing.command import CommandState, OutboxCommand

from ._base import SqliteRepository


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
        """Persist durable envelope fields; the signed envelope token remains transient."""
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

    def claim_with_lease(
        self,
        where: Mapping[str, object],
        *,
        owner: str,
        lease_ms: int,
        now_ms: int,
    ):
        return claim_with_lease(self.connection, "outbox_commands", where, owner, lease_ms, now_ms=now_ms)

    def complete(
        self,
        command_id: str,
        lease_token: str,
        *,
        acked_at_ms: int,
        updated_at_ms: int,
    ) -> bool:
        return complete_with_lease(
            self.connection,
            "outbox_commands",
            command_id,
            lease_token,
            fields={
                "state": CommandState.ACKED,
                "acked_at": acked_at_ms,
                "updated_at": updated_at_ms,
            },
        )
