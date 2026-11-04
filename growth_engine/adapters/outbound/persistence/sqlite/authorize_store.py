from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime, timezone

from growth_engine.application.ports.uow import UnitOfWork
from growth_engine.application.publishing.authorize_publish import AuthorizeCandidate
from growth_engine.domain.kernel.hashing import canonical_json_bytes
from growth_engine.domain.ops.incident import (
    Incident,
    IncidentSeverity,
    IncidentState,
    incident_fingerprint,
)


class SqliteAuthorizePublishStore:
    """Read and commit the authorize gate through real SQLite UoW transactions."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork], environment: str, clock) -> None:
        if environment not in {"test", "production"}:
            raise ValueError("environment must be test or production")
        self._uow_factory = uow_factory
        self._environment = environment
        self._clock = clock

    def resolve_channel_by_key(self, channel_key: str):
        with self._uow_factory().read_only() as tx:
            row = tx.connection.execute(
                "SELECT id FROM channels WHERE channel_key=? AND environment=?",
                (channel_key, self._environment),
            ).fetchone()
            return None if row is None else tx.channels.get_channel(row["id"])

    def read_candidate(self, command_id: str) -> AuthorizeCandidate | None:
        with self._uow_factory().read_only() as tx:
            return self._get_candidate(tx, command_id, self._clock.now_ms(), self._environment)

    @contextmanager
    def begin_immediate(self) -> Iterator["SqliteAuthorizeTransaction"]:
        with self._uow_factory().begin_immediate() as tx:
            yield SqliteAuthorizeTransaction(tx, self._environment, self._clock)

    @staticmethod
    def _get_candidate(
        tx: UnitOfWork, command_id: str, now_ms: int, environment: str
    ) -> AuthorizeCandidate | None:
        row = tx.connection.execute(
            """SELECT c.payload_hash AS command_payload_hash, c.dispatch_epoch,
                      c.state AS command_state, d.id AS delivery_id, d.state AS delivery_state,
                      d.row_version, d.permalink, d.current_revision_id, d.active_approval_id,
                      d.channel_id, d.package_id, d.active,
                      r.payload_json, r.payload_hash AS revision_hash,
                      r.channel_config_id, r.variant_id, r.qc_report_id,
                      p.fact_snapshot_json, p.fact_snapshot_hash
               FROM outbox_commands c
               JOIN deliveries d ON d.id=c.delivery_id
               JOIN delivery_revisions r ON r.id=d.current_revision_id AND r.delivery_id=d.id
               JOIN channels ch ON ch.id=d.channel_id AND ch.environment=?
               JOIN content_packages p ON p.id=d.package_id
               WHERE c.id=?""",
            (environment, command_id),
        ).fetchone()
        if row is None:
            return None
        # The command token is transient. A sentinel is sufficient for domain state transitions;
        # only the verified inbound token is returned to Make.
        command = tx.commands.get(command_id, envelope_token="transient-not-persisted")
        delivery = tx.deliveries.get(row["delivery_id"])
        revision = tx.deliveries.get_revision(row["current_revision_id"])
        channel = tx.channels.get_channel(row["channel_id"])
        config = tx.channels.get_config(row["channel_config_id"])
        approval = (
            tx.deliveries.get_approval(row["active_approval_id"])
            if row["active_approval_id"]
            else None
        )
        variant = tx.media.get_variant(row["variant_id"])
        report = tx.qc.get(row["qc_report_id"])
        if any(value is None for value in (command, delivery, revision, channel, config, variant, report)):
            return None
        revoked = bool(
            tx.connection.execute(
                "SELECT 1 FROM approval_decisions WHERE decision='REVOKE' AND revokes_id=? LIMIT 1",
                (row["active_approval_id"],),
            ).fetchone()
        )
        live = bool(
            tx.connection.execute(
                "SELECT 1 FROM executions WHERE delivery_id=? "
                "AND state IN ('AUTHORIZED','REPORTED','UNKNOWN') LIMIT 1",
                (row["delivery_id"],),
            ).fetchone()
        )
        return AuthorizeCandidate(
            command=command,
            command_payload_hash=row["command_payload_hash"],
            command_dispatch_epoch=row["dispatch_epoch"],
            delivery=delivery,
            current_revision_id=row["current_revision_id"],
            active_approval_id=row["active_approval_id"],
            revision=revision,
            approval=approval,
            approval_revoked=revoked,
            channel=channel,
            channel_config=config,
            variant=variant,
            qc_report=report,
            facts_valid=_facts_valid(row["fact_snapshot_json"], row["fact_snapshot_hash"], now_ms),
            has_live_execution=live,
        )


class SqliteAuthorizeTransaction:
    def __init__(self, uow: UnitOfWork, environment: str, clock) -> None:
        self._uow = uow
        self._environment = environment
        self._clock = clock

    @property
    def connection(self):
        return self._uow.connection

    def current_controls(self):
        return self._uow.controls.get(self._environment)

    def get_candidate(self, command_id: str) -> AuthorizeCandidate | None:
        return SqliteAuthorizePublishStore._get_candidate(
            self._uow, command_id, self._clock.now_ms(), self._environment
        )

    def commit_authorized(
        self,
        candidate,
        command,
        delivery,
        execution,
        *,
        principal_id: str,
        expected_row_version: int,
        audit_event_id: str,
        correlation_id: str,
        at_ms: int,
    ) -> bool:
        connection = self.connection
        connection.execute("SAVEPOINT authorize_publish")
        updated_delivery = connection.execute(
            """UPDATE deliveries SET state='EXECUTING', row_version=row_version+1, updated_at=?
               WHERE id=? AND row_version=? AND state='QUEUED' AND active=1
                 AND current_revision_id=? AND active_approval_id=?""",
            (
                at_ms,
                candidate.delivery.id,
                expected_row_version,
                candidate.current_revision_id,
                candidate.active_approval_id,
            ),
        )
        updated_command = connection.execute(
            """UPDATE outbox_commands SET state='AUTHORIZED', lease_owner=NULL, lease_token=NULL,
                      lease_until=NULL, updated_at=?
               WHERE id=? AND delivery_id=? AND revision_id=? AND payload_hash=?
                 AND dispatch_epoch=? AND state IN ('PENDING','DELIVERING','ACKED')""",
            (
                at_ms,
                candidate.command.id,
                candidate.delivery.id,
                candidate.current_revision_id,
                candidate.command_payload_hash,
                candidate.command_dispatch_epoch,
            ),
        )
        if updated_delivery.rowcount != 1 or updated_command.rowcount != 1:
            connection.execute("ROLLBACK TO authorize_publish")
            connection.execute("RELEASE authorize_publish")
            return False
        connection.execute(
            """INSERT INTO executions
               (id, command_id, delivery_id, principal_id, state, grant_id, authorized_at,
                grant_expires_at, receipt_due_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                execution.id,
                execution.command_id,
                execution.delivery_id,
                principal_id,
                execution.state.value,
                execution.grant_id,
                at_ms,
                execution.grant_expires_at_ms,
                execution.receipt_due_at_ms,
                at_ms,
            ),
        )
        self._uow.audit.append(
            event_id=audit_event_id,
            aggregate_type="delivery",
            aggregate_id=candidate.delivery.id,
            actor="growth-engine",
            action="publish.command_authorized",
            before_hash=candidate.command_payload_hash,
            after_hash=candidate.command_payload_hash,
            details_json=canonical_json_bytes(
                {"command_id": candidate.command.id, "execution_id": execution.id}
            ).decode("utf-8"),
            correlation_id=correlation_id,
            created_at_ms=at_ms,
        )
        connection.execute("RELEASE authorize_publish")
        return True

    def commit_blocked(
        self,
        candidate,
        command,
        delivery,
        *,
        expected_row_version: int,
        blocked_reason: str,
        audit_event_id: str,
        incident_id: str,
        correlation_id: str,
        at_ms: int,
    ) -> bool:
        connection = self.connection
        connection.execute("SAVEPOINT block_publish")
        updated_delivery = connection.execute(
            """UPDATE deliveries SET state='BLOCKED', blocked_reason=?,
                      row_version=row_version+1, updated_at=?
               WHERE id=? AND row_version=? AND state='QUEUED' AND active=1
                 AND current_revision_id=? AND active_approval_id=?""",
            (
                blocked_reason,
                at_ms,
                candidate.delivery.id,
                expected_row_version,
                candidate.current_revision_id,
                candidate.active_approval_id,
            ),
        )
        updated_command = connection.execute(
            """UPDATE outbox_commands SET state='CANCELLED', lease_owner=NULL, lease_token=NULL,
                      lease_until=NULL, updated_at=?
               WHERE id=? AND delivery_id=? AND state IN ('PENDING','DELIVERING','ACKED')""",
            (at_ms, candidate.command.id, candidate.delivery.id),
        )
        if updated_delivery.rowcount != 1 or updated_command.rowcount != 1:
            connection.execute("ROLLBACK TO block_publish")
            connection.execute("RELEASE block_publish")
            return False
        incident = Incident(
            id=incident_id,
            type="PREFLIGHT_BLOCKED",
            fingerprint=incident_fingerprint(
                "PREFLIGHT_BLOCKED", candidate.channel.id, candidate.delivery.id
            ),
            channel_id=candidate.channel.id,
            ref=candidate.delivery.id,
            severity=IncidentSeverity.HIGH,
            state=IncidentState.OPEN,
            first_seen_at_ms=at_ms,
            last_seen_at_ms=at_ms,
        )
        self._uow.incidents.open_or_touch(
            incident,
            details_json=canonical_json_bytes({"reason": blocked_reason}).decode("utf-8"),
        )
        self._append_authorize_audit(
            candidate,
            audit_event_id=audit_event_id,
            action="publish.preflight_blocked",
            correlation_id=correlation_id,
            at_ms=at_ms,
            details={"reason": blocked_reason},
        )
        connection.execute("RELEASE block_publish")
        return True

    def commit_expired(
        self,
        candidate,
        command,
        delivery,
        *,
        expected_row_version: int,
        audit_event_id: str,
        correlation_id: str,
        at_ms: int,
    ) -> bool:
        connection = self.connection
        connection.execute("SAVEPOINT expire_authorize")
        updated_delivery = connection.execute(
            """UPDATE deliveries SET state='EXPIRED', row_version=row_version+1, updated_at=?
               WHERE id=? AND row_version=? AND state='QUEUED' AND active=1
                 AND current_revision_id=? AND active_approval_id=?""",
            (
                at_ms,
                candidate.delivery.id,
                expected_row_version,
                candidate.current_revision_id,
                candidate.active_approval_id,
            ),
        )
        updated_command = connection.execute(
            """UPDATE outbox_commands SET state='EXPIRED', lease_owner=NULL, lease_token=NULL,
                      lease_until=NULL, updated_at=?
               WHERE id=? AND delivery_id=? AND state IN ('PENDING','DELIVERING','ACKED')""",
            (at_ms, candidate.command.id, candidate.delivery.id),
        )
        if updated_delivery.rowcount != 1 or updated_command.rowcount != 1:
            connection.execute("ROLLBACK TO expire_authorize")
            connection.execute("RELEASE expire_authorize")
            return False
        self._append_authorize_audit(
            candidate,
            audit_event_id=audit_event_id,
            action="publish.command_expired",
            correlation_id=correlation_id,
            at_ms=at_ms,
            details={},
        )
        connection.execute("RELEASE expire_authorize")
        return True

    def _append_authorize_audit(
        self,
        candidate,
        *,
        audit_event_id: str,
        action: str,
        correlation_id: str,
        at_ms: int,
        details: dict[str, object],
    ) -> None:
        self._uow.audit.append(
            event_id=audit_event_id,
            aggregate_type="delivery",
            aggregate_id=candidate.delivery.id,
            actor="growth-engine",
            action=action,
            before_hash=candidate.command_payload_hash,
            after_hash=candidate.command_payload_hash,
            details_json=canonical_json_bytes(details).decode("utf-8"),
            correlation_id=correlation_id,
            created_at_ms=at_ms,
        )


def _facts_valid(facts_json: str, expected_hash: str, at_ms: int) -> bool:
    try:
        if hashlib.sha256(facts_json.encode("utf-8")).hexdigest() != expected_hash:
            return False
        facts = json.loads(facts_json)
        if not isinstance(facts, dict):
            return False
        moment = datetime.fromtimestamp(at_ms / 1000, tz=timezone.utc)
        for fact in facts.values():
            if not isinstance(fact, dict):
                return False
            valid_from = _parse_fact_time(fact.get("valid_from"))
            valid_to_raw = fact.get("valid_to")
            valid_to = _parse_fact_time(valid_to_raw) if valid_to_raw else None
            if valid_from is None or (valid_to_raw and valid_to is None):
                return False
            if moment < valid_from or (valid_to is not None and moment > valid_to):
                return False
        return True
    except (TypeError, ValueError, json.JSONDecodeError, OverflowError, OSError):
        return False


def _parse_fact_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
