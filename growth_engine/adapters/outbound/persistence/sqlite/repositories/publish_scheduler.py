from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager

from growth_engine.application.ports.uow import UnitOfWork
from growth_engine.application.publishing.enqueue_due import EnqueueCandidate
from growth_engine.application.publishing.expire_overdue import ExpireCandidate
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.revision import DeliveryRevision
from growth_engine.domain.delivery.states import DeliveryState
from growth_engine.domain.kernel.hashing import canonical_json_bytes
from growth_engine.domain.publishing.command import OutboxCommand
from growth_engine.domain.publishing.runtime_mode import RuntimeControls


class SqlitePublishSchedulerStore:
    """SQLite transaction adapter for enqueue-due and overdue-expiry workflows."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork], environment: str) -> None:
        if environment not in {"test", "production"}:
            raise ValueError("environment must be test or production")
        self._uow_factory = uow_factory
        self._environment = environment

    def read_controls(self) -> RuntimeControls | None:
        with self._uow_factory().read_only() as tx:
            return tx.controls.get(self._environment)

    def due_approved(self, now_ms: int, limit: int) -> Sequence[str]:
        with self._uow_factory().read_only() as tx:
            rows = tx.connection.execute(
                """SELECT d.id
                   FROM deliveries d
                   JOIN delivery_revisions r ON r.id=d.current_revision_id
                   JOIN channels c ON c.id=d.channel_id
                   WHERE d.active=1 AND d.state='APPROVED'
                     AND c.environment=? AND c.enabled=1
                     AND r.scheduled_at<=? AND r.deadline_at>=?
                   ORDER BY r.scheduled_at, d.id LIMIT ?""",
                (self._environment, now_ms, now_ms, limit),
            ).fetchall()
        return tuple(row["id"] for row in rows)

    def overdue_delivery_ids(self, now_ms: int) -> Sequence[str]:
        with self._uow_factory().read_only() as tx:
            rows = tx.connection.execute(
                """SELECT d.id
                   FROM deliveries d
                   JOIN slot_targets t ON t.id=d.target_id AND t.channel_id=d.channel_id
                   JOIN slots s ON s.id=t.slot_id
                   JOIN channels c ON c.id=d.channel_id
                   LEFT JOIN delivery_revisions r ON r.id=d.current_revision_id
                   WHERE d.active=1 AND d.state IN ('DRAFT','IN_REVIEW','APPROVED','QUEUED','BLOCKED')
                     AND c.environment=? AND COALESCE(r.deadline_at,s.deadline_at)<?
                   ORDER BY COALESCE(r.deadline_at,s.deadline_at), d.id""",
                (self._environment, now_ms),
            ).fetchall()
        return tuple(row["id"] for row in rows)

    @contextmanager
    def begin_immediate(self) -> Iterator["SqlitePublishSchedulerTransaction"]:
        with self._uow_factory().begin_immediate() as tx:
            yield SqlitePublishSchedulerTransaction(tx, self._environment)


class SqlitePublishSchedulerTransaction:
    def __init__(self, uow: UnitOfWork, environment: str) -> None:
        self._uow = uow
        self._environment = environment

    def current_controls(self) -> RuntimeControls | None:
        return self._uow.controls.get(self._environment)

    def get_enqueue_candidate(self, delivery_id: str) -> EnqueueCandidate | None:
        row = self._uow.connection.execute(
            """SELECT d.id, d.state, d.row_version, d.permalink, d.current_revision_id,
                      d.active_approval_id, d.channel_id, r.payload_json, r.payload_hash,
                      r.channel_config_id
               FROM deliveries d
               JOIN delivery_revisions r ON r.id=d.current_revision_id AND r.delivery_id=d.id
               JOIN channels c ON c.id=d.channel_id
               WHERE d.id=? AND d.active=1 AND c.environment=?""",
            (delivery_id, self._environment),
        ).fetchone()
        if row is None or not row["active_approval_id"]:
            return None
        delivery = self._uow.deliveries.get(delivery_id)
        channel = self._uow.channels.get_channel(row["channel_id"])
        config = self._uow.channels.get_config(row["channel_config_id"])
        revision = DeliveryRevision(row["payload_json"], row["payload_hash"])
        approval = self._uow.deliveries.get_approval(row["active_approval_id"])
        if delivery is None or channel is None or config is None:
            return None
        revoked = self._uow.connection.execute(
            "SELECT 1 FROM approval_decisions WHERE decision='REVOKE' AND revokes_id=? LIMIT 1",
            (row["active_approval_id"],),
        ).fetchone() is not None
        return EnqueueCandidate(
            delivery=delivery,
            current_revision_id=row["current_revision_id"],
            active_approval_id=row["active_approval_id"],
            revision=revision,
            approval=approval,
            approval_revoked=revoked,
            channel=channel,
            channel_config=config,
        )

    def commit_enqueue(
        self,
        candidate: EnqueueCandidate,
        command: OutboxCommand,
        updated_delivery: Delivery,
        *,
        expected_row_version: int,
        dispatch_epoch: str,
        at_ms: int,
        audit_event_id: str,
        correlation_id: str,
    ) -> bool:
        connection = self._uow.connection
        connection.execute("SAVEPOINT enqueue_publish_command")
        try:
            updated = connection.execute(
                """UPDATE deliveries SET state=?, row_version=row_version+1, updated_at=?
                   WHERE id=? AND row_version=? AND state='APPROVED' AND active=1
                     AND current_revision_id=? AND active_approval_id=?""",
                (
                    updated_delivery.state.value,
                    at_ms,
                    candidate.delivery.id,
                    expected_row_version,
                    candidate.current_revision_id,
                    candidate.active_approval_id,
                ),
            )
            if updated.rowcount != 1:
                connection.execute("ROLLBACK TO enqueue_publish_command")
                connection.execute("RELEASE enqueue_publish_command")
                return False
            self._uow.commands.save(
                command,
                payload_hash=candidate.revision.payload_hash,
                dispatch_epoch=dispatch_epoch,
                created_at_ms=at_ms,
                updated_at_ms=at_ms,
            )
            self._uow.audit.append(
                event_id=audit_event_id,
                aggregate_type="delivery",
                aggregate_id=candidate.delivery.id,
                actor="growth-engine",
                action="publish.command_enqueued",
                before_hash=candidate.revision.payload_hash,
                after_hash=candidate.revision.payload_hash,
                details_json=canonical_json_bytes(
                    {"command_id": command.id, "business_key": command.business_key, "state": command.state.value}
                ).decode("utf-8"),
                correlation_id=correlation_id,
                created_at_ms=at_ms,
            )
            connection.execute("RELEASE enqueue_publish_command")
            return True
        except sqlite3.IntegrityError as error:
            connection.execute("ROLLBACK TO enqueue_publish_command")
            connection.execute("RELEASE enqueue_publish_command")
            if "UNIQUE constraint failed" in str(error):
                return False
            raise

    def get_expire_candidate(self, delivery_id: str) -> ExpireCandidate | None:
        row = self._uow.connection.execute(
            """SELECT d.id, d.state, d.row_version, d.permalink,
                      COALESCE(r.deadline_at,s.deadline_at) AS deadline_at
               FROM deliveries d
               JOIN slot_targets t ON t.id=d.target_id AND t.channel_id=d.channel_id
               JOIN slots s ON s.id=t.slot_id
               LEFT JOIN delivery_revisions r ON r.id=d.current_revision_id
               JOIN channels c ON c.id=d.channel_id
               WHERE d.id=? AND d.active=1 AND c.environment=?""",
            (delivery_id, self._environment),
        ).fetchone()
        if row is None:
            return None
        delivery = Delivery(
            id=row["id"],
            state=DeliveryState(row["state"]),
            row_version=row["row_version"],
            permalink=row["permalink"],
        )
        live = self._uow.connection.execute(
            "SELECT 1 FROM executions WHERE delivery_id=? AND state IN ('AUTHORIZED','REPORTED','UNKNOWN') LIMIT 1",
            (delivery_id,),
        ).fetchone() is not None
        return ExpireCandidate(delivery, row["deadline_at"], live)

    def commit_expire(
        self,
        candidate: ExpireCandidate,
        updated_delivery: Delivery,
        *,
        expected_row_version: int,
        at_ms: int,
        audit_event_id: str,
        correlation_id: str,
    ) -> bool:
        connection = self._uow.connection
        connection.execute("SAVEPOINT expire_overdue_delivery")
        updated = connection.execute(
            """UPDATE deliveries SET state=?, row_version=row_version+1, updated_at=?
               WHERE id=? AND row_version=? AND state=? AND active=1""",
            (
                updated_delivery.state.value,
                at_ms,
                candidate.delivery.id,
                expected_row_version,
                candidate.delivery.state.value,
            ),
        )
        if updated.rowcount != 1:
            connection.execute("ROLLBACK TO expire_overdue_delivery")
            connection.execute("RELEASE expire_overdue_delivery")
            return False
        self._uow.commands.close_open_for_delivery(candidate.delivery.id, at_ms)
        self._uow.audit.append(
            event_id=audit_event_id,
            aggregate_type="delivery",
            aggregate_id=candidate.delivery.id,
            actor="growth-engine",
            action="publish.delivery_expired",
            before_hash=None,
            after_hash=None,
            details_json=canonical_json_bytes(
                {"deadline_at_ms": candidate.deadline_at_ms, "state": updated_delivery.state.value}
            ).decode("utf-8"),
            correlation_id=correlation_id,
            created_at_ms=at_ms,
        )
        connection.execute("RELEASE expire_overdue_delivery")
        return True
