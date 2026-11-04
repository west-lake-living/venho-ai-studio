from __future__ import annotations

from collections.abc import Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Protocol

from growth_engine.application.ports.clock import IdGenerator
from growth_engine.domain.channels.channel import Channel, ChannelConfig, config_hash
from growth_engine.domain.delivery.approval import ApprovalDecision, ApprovalType
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.revision import DeliveryRevision
from growth_engine.domain.delivery.states import DeliveryEvent, DeliveryState
from growth_engine.domain.kernel.errors import DomainError
from growth_engine.domain.publishing.command import OutboxCommand
from growth_engine.domain.publishing.runtime_mode import PublishMode, RuntimeControls


@dataclass(frozen=True)
class EnqueueCandidate:
    delivery: Delivery
    current_revision_id: str
    active_approval_id: str | None
    revision: DeliveryRevision
    approval: ApprovalDecision | None
    approval_revoked: bool
    channel: Channel
    channel_config: ChannelConfig

    def __post_init__(self) -> None:
        if not self.current_revision_id.strip():
            raise ValueError("current_revision_id is required")
        if type(self.approval_revoked) is not bool:
            raise ValueError("approval_revoked must be a boolean")


@dataclass(frozen=True)
class EnqueueDueResult:
    enqueued_delivery_ids: tuple[str, ...] = ()
    skipped_delivery_ids: tuple[str, ...] = ()
    skipped_reason: str | None = None


@dataclass(frozen=True)
class EnqueueCommandClaims:
    command_id: str
    delivery_id: str
    revision_id: str
    channel_id: str
    remote_account_id: str
    payload_hash: str
    dispatch_epoch: str
    audience: str
    expires_at_ms: int


class CapabilityTokenIssuer(Protocol):
    def issue(self, claims: EnqueueCommandClaims) -> str: ...


class EnqueueTransaction(Protocol):
    def current_controls(self) -> RuntimeControls | None: ...
    def get_enqueue_candidate(self, delivery_id: str) -> EnqueueCandidate | None: ...

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
    ) -> bool: ...


class EnqueueDueStore(Protocol):
    def read_controls(self) -> RuntimeControls | None: ...
    def due_approved(self, now_ms: int, limit: int) -> Sequence[str]: ...
    def begin_immediate(self) -> AbstractContextManager[EnqueueTransaction]: ...


class EnqueueDue:
    """Create one durable outbox command for each currently eligible delivery."""

    def __init__(
        self,
        store: EnqueueDueStore,
        tokens: CapabilityTokenIssuer,
        ids: IdGenerator,
    ) -> None:
        self._store = store
        self._tokens = tokens
        self._ids = ids

    def execute(self, now_ms: int, limit: int = 20) -> EnqueueDueResult:
        if type(now_ms) is not int or now_ms < 0:
            raise ValueError("now_ms must be a non-negative integer")
        if type(limit) is not int or limit < 1:
            raise ValueError("limit must be a positive integer")

        controls = self._store.read_controls()
        if controls is None:
            return EnqueueDueResult(skipped_reason="CONTROLS_UNAVAILABLE")
        if controls.mode is not PublishMode.LIVE_MANUAL:
            return EnqueueDueResult(skipped_reason="MODE_NOT_LIVE_MANUAL")
        if controls.global_pause:
            return EnqueueDueResult(skipped_reason="GLOBAL_PAUSE")

        delivery_ids = tuple(dict.fromkeys(self._store.due_approved(now_ms, limit)))
        enqueued: list[str] = []
        skipped: list[str] = []
        for delivery_id in delivery_ids:
            if not isinstance(delivery_id, str) or not delivery_id.strip():
                raise ValueError("due_approved must return non-empty delivery ids")
            with self._store.begin_immediate() as tx:
                current = tx.current_controls()
                candidate = tx.get_enqueue_candidate(delivery_id)
                if current is None or candidate is None or not _eligible(candidate, now_ms, current):
                    skipped.append(delivery_id)
                    continue

                revision = candidate.revision
                payload = revision.payload
                command_id = self._ids.new_id()
                token = self._tokens.issue(
                    EnqueueCommandClaims(
                        command_id=command_id,
                        delivery_id=candidate.delivery.id,
                        revision_id=candidate.current_revision_id,
                        channel_id=candidate.channel.id,
                        remote_account_id=candidate.channel.remote_account_id,
                        payload_hash=revision.payload_hash,
                        dispatch_epoch=current.dispatch_epoch,
                        audience=f"make-route:{candidate.channel.id}",
                        expires_at_ms=payload["deadline_at_ms"],
                    )
                )
                command = OutboxCommand.new(
                    command_id=command_id,
                    delivery_id=candidate.delivery.id,
                    revision_id=candidate.current_revision_id,
                    sequence_no=1,
                    expires_at_ms=payload["deadline_at_ms"],
                    now_ms=now_ms,
                    envelope_token=token,
                )
                updated_delivery, _events = candidate.delivery.apply(
                    DeliveryEvent.ENQUEUE,
                    {
                        "now_ms": now_ms,
                        "scheduled_at_ms": payload["scheduled_at_ms"],
                        "deadline_at_ms": payload["deadline_at_ms"],
                        "mode": current.mode.value,
                        "paused": candidate.channel.paused or current.global_pause,
                        "epoch_current": bool(current.dispatch_epoch.strip()),
                    },
                )
                correlation_id = f"publish-enqueue:{candidate.delivery.id}:{now_ms}"
                inserted = tx.commit_enqueue(
                    candidate,
                    command,
                    updated_delivery,
                    expected_row_version=candidate.delivery.row_version,
                    dispatch_epoch=current.dispatch_epoch,
                    at_ms=now_ms,
                    audit_event_id=self._ids.new_id(),
                    correlation_id=correlation_id,
                )
                if inserted:
                    enqueued.append(candidate.delivery.id)
                else:
                    skipped.append(candidate.delivery.id)

        return EnqueueDueResult(tuple(enqueued), tuple(skipped))


def _eligible(candidate: EnqueueCandidate, now_ms: int, controls: RuntimeControls) -> bool:
    delivery = candidate.delivery
    channel = candidate.channel
    config = candidate.channel_config
    revision = candidate.revision
    payload = revision.payload
    approval = candidate.approval
    scheduled_at = payload.get("scheduled_at_ms")
    deadline_at = payload.get("deadline_at_ms")

    return (
        delivery.state is DeliveryState.APPROVED
        and controls.mode is PublishMode.LIVE_MANUAL
        and not controls.global_pause
        and channel.enabled
        and not channel.paused
        and channel.platform.value == "facebook"
        and config.channel_id == channel.id
        and payload.get("revision_id") == candidate.current_revision_id
        and payload.get("delivery_id") == delivery.id
        and payload.get("channel_id") == channel.id
        and payload.get("remote_account_id") == channel.remote_account_id
        and payload.get("channel_config_hash") == config_hash(config)
        and candidate.active_approval_id is not None
        and approval is not None
        and approval.id == candidate.active_approval_id
        and approval.decision is ApprovalType.APPROVE
        and approval.revision_id == candidate.current_revision_id
        and approval.payload_hash == revision.payload_hash
        and not candidate.approval_revoked
        and type(scheduled_at) is int
        and type(deadline_at) is int
        and scheduled_at <= now_ms <= deadline_at
        and bool(controls.dispatch_epoch.strip())
    )
