from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping, Sequence

from growth_engine.application.ports.uow import UnitOfWork
from growth_engine.application.publishing.dispatch_outbox import DispatchLease
from growth_engine.application.publishing.enqueue_due import EnqueueCommandClaims
from growth_engine.domain.publishing.command import CommandState, OutboxCommand
from growth_engine.domain.publishing.runtime_mode import PublishMode
from growth_engine.domain.publishing.window import PublishingPolicy


_ROUTE_REF = re.compile(r"GE_MAKE_WEBHOOK_URL_([A-Z0-9_]+)\Z")


class SqliteDispatchStore:
    """Claim and complete publish commands using one fenced SQLite transaction."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        environment: str,
        make_webhook_urls: Mapping[str, str],
        token_issuer: object,
        *,
        redeliver_after_ack_minutes: int,
    ) -> None:
        if environment not in {"test", "production"}:
            raise ValueError("environment must be test or production")
        if type(redeliver_after_ack_minutes) is not int or redeliver_after_ack_minutes < 1:
            raise ValueError("redeliver_after_ack_minutes must be positive")
        self._uow_factory = uow_factory
        self._environment = environment
        self._routes = dict(make_webhook_urls)
        self._tokens = token_issuer
        self._redeliver_after_ack_ms = redeliver_after_ack_minutes * 60_000

    def claim_due(
        self,
        now_ms: int,
        limit: int,
        *,
        owner: str,
        lease_ms: int,
        policy: PublishingPolicy,
    ) -> Sequence[DispatchLease]:
        if type(now_ms) is not int or now_ms < 0 or type(limit) is not int or limit < 1:
            raise ValueError("now_ms and limit are invalid")
        claimed: list[DispatchLease] = []
        with self._uow_factory().begin_immediate() as tx:
            controls = tx.controls.get(self._environment)
            if controls is None or controls.mode is not PublishMode.LIVE_MANUAL or controls.global_pause:
                return ()
            rows = tx.connection.execute(
                """SELECT c.id AS command_id, c.delivery_id, c.revision_id, c.sequence_no,
                          c.business_key, c.payload_hash, c.dispatch_epoch, c.state AS command_state,
                          c.expires_at, c.next_attempt_at, c.transport_attempts, c.acked_at,
                          c.lease_token, c.lease_until, c.signing_key_id,
                          d.current_revision_id, d.active_approval_id, d.channel_id,
                          r.payload_json, r.payload_hash AS revision_hash, r.variant_id,
                          a.decision AS approval_decision, ch.remote_account_id, ch.enabled,
                          ch.paused, ch.platform, cfg.make_route_ref, mv.sha256 AS media_sha256
                   FROM outbox_commands c
                   JOIN deliveries d ON d.id=c.delivery_id
                   JOIN delivery_revisions r ON r.id=d.current_revision_id AND r.delivery_id=d.id
                   JOIN approval_decisions a ON a.id=d.active_approval_id AND a.revision_id=r.id
                   JOIN channels ch ON ch.id=d.channel_id
                   JOIN channel_configs cfg ON cfg.id=r.channel_config_id AND cfg.channel_id=ch.id
                   JOIN media_variants mv ON mv.id=r.variant_id
                   WHERE c.kind='PUBLISH' AND c.signing_key_id IS NOT NULL
                     AND c.expires_at>=? AND c.dispatch_epoch=? AND c.payload_hash=r.payload_hash
                     AND d.active=1 AND d.state='QUEUED' AND d.current_revision_id=c.revision_id
                     AND d.channel_id=ch.id AND a.decision='APPROVE'
                     AND NOT EXISTS (
                       SELECT 1 FROM approval_decisions rev
                       WHERE rev.decision='REVOKE' AND rev.revokes_id=a.id
                     )
                     AND ch.environment=? AND ch.enabled=1 AND ch.paused=0
                     AND ch.platform='facebook' AND cfg.id=r.channel_config_id
                     AND mv.qc_status='PASS'
                     AND ((c.state IN ('PENDING','ACKED') AND c.next_attempt_at<=?)
                       OR (c.state='DELIVERING' AND c.lease_until<=?))
                     AND (c.state='ACKED' OR c.transport_attempts < ?)
                   ORDER BY c.next_attempt_at, c.created_at, c.id LIMIT ?""",
                (
                    now_ms,
                    controls.dispatch_epoch,
                    self._environment,
                    now_ms,
                    now_ms,
                    policy.max_transport_attempts,
                    limit,
                ),
            ).fetchall()
            for row in rows:
                route = self._resolve_route(row["make_route_ref"])
                if (
                    route is None
                    or not row["signing_key_id"]
                    or not self._payload_matches(row)
                ):
                    continue
                where: dict[str, object | tuple[str, object]] = {
                    "id": row["command_id"],
                    "state": row["command_state"],
                    "expires_at": (">=", now_ms),
                }
                if row["command_state"] == "DELIVERING":
                    where["lease_until"] = ("<=", now_ms)
                else:
                    where["next_attempt_at"] = ("<=", now_ms)
                result = tx.commands.claim_with_lease(
                    where, owner=owner, lease_ms=lease_ms, now_ms=now_ms
                )
                if result is None:
                    continue
                claimed_row, lease_token = result
                command = OutboxCommand(
                    id=claimed_row["id"],
                    delivery_id=claimed_row["delivery_id"],
                    revision_id=claimed_row["revision_id"],
                    sequence_no=claimed_row["sequence_no"],
                    business_key=claimed_row["business_key"],
                    expires_at_ms=claimed_row["expires_at"],
                    next_attempt_at_ms=claimed_row["next_attempt_at"],
                    envelope_token=self._issue_token(row, signing_key_id=row["signing_key_id"]),
                    state=CommandState.DELIVERING,
                    attempts=claimed_row["transport_attempts"],
                    lease_token=lease_token,
                    lease_expires_at_ms=claimed_row["lease_until"],
                    acked_at_ms=claimed_row["acked_at"],
                )
                claimed.append(
                    DispatchLease(
                        command=command,
                        lease_token=lease_token,
                        environment=self._environment,
                        channel_id=row["channel_id"],
                        remote_page_id=row["remote_account_id"],
                        payload_hash=row["revision_hash"],
                        dispatch_epoch=row["dispatch_epoch"],
                        route_ref=route,
                        media_sha256=row["media_sha256"],
                    )
                )
        return tuple(claimed)

    def complete_ack(self, lease: DispatchLease, *, at_ms: int) -> bool:
        with self._uow_factory().begin_immediate() as tx:
            return tx.commands.complete(
                lease.command.id,
                lease.lease_token,
                acked_at_ms=at_ms,
                next_attempt_at_ms=at_ms + self._redeliver_after_ack_ms,
                updated_at_ms=at_ms,
            )

    def complete_retry(self, lease: DispatchLease, command: OutboxCommand, *, at_ms: int) -> bool:
        with self._uow_factory().begin_immediate() as tx:
            return tx.commands.complete_retry(
                lease.command.id,
                lease.lease_token,
                next_attempt_at_ms=command.next_attempt_at_ms,
                transport_attempts=command.attempts,
                last_error="transport_retry",
                updated_at_ms=at_ms,
            )

    def complete_fatal(
        self,
        lease: DispatchLease,
        *,
        at_ms: int,
        status: int | None,
        next_attempt_at_ms: int,
    ) -> bool:
        safe_status = str(status) if status is not None else "unknown"
        with self._uow_factory().begin_immediate() as tx:
            return tx.commands.complete_fatal(
                lease.command.id,
                lease.lease_token,
                next_attempt_at_ms=next_attempt_at_ms,
                transport_attempts=lease.command.attempts + 1,
                last_error=f"transport_fatal_http_{safe_status}",
                updated_at_ms=at_ms,
            )

    def _resolve_route(self, route_ref: str) -> str | None:
        match = _ROUTE_REF.fullmatch(route_ref)
        if match is None:
            return None
        value = self._routes.get(match.group(1), "")
        if not isinstance(value, str) or not value.startswith("https://"):
            return None
        return value

    @staticmethod
    def _payload_matches(row) -> bool:
        try:
            payload = json.loads(row["payload_json"])
            return (
                isinstance(payload, dict)
                and payload.get("delivery_id") == row["delivery_id"]
                and payload.get("revision_id") == row["revision_id"]
                and payload.get("channel_id") == row["channel_id"]
                and payload.get("remote_account_id") == row["remote_account_id"]
                and payload.get("deadline_at_ms") == row["expires_at"]
                and any(
                    isinstance(media, dict) and media.get("sha256") == row["media_sha256"]
                    for media in payload.get("media", ())
                )
            )
        except (TypeError, ValueError, json.JSONDecodeError):
            return False

    def _issue_token(self, row, *, signing_key_id: str) -> str:
        claims = EnqueueCommandClaims(
            command_id=row["command_id"],
            delivery_id=row["delivery_id"],
            revision_id=row["revision_id"],
            channel_id=row["channel_id"],
            remote_account_id=row["remote_account_id"],
            payload_hash=row["revision_hash"],
            dispatch_epoch=row["dispatch_epoch"],
            audience=f"make-route:{row['channel_id']}",
            expires_at_ms=row["expires_at"],
        )
        return self._tokens.issue(claims, key_id=signing_key_id)
