from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from growth_engine.application.errors import Conflict, NotFound
from growth_engine.application.ports.clock import Clock, IdGenerator
from growth_engine.domain.delivery.approval import ApprovalDecision, ApprovalType
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.revision import DeliveryRevision
from growth_engine.domain.delivery.states import DeliveryEvent, DeliveryState
from growth_engine.domain.kernel.errors import DomainError, ErrorCode


@dataclass(frozen=True)
class RevokeContext:
    delivery: Delivery
    current_revision: DeliveryRevision
    active_approval: ApprovalDecision | None
    command_state: str | None
    live_execution: bool


@dataclass(frozen=True)
class RevokeWrite:
    context: RevokeContext
    updated_delivery: Delivery
    revocation: ApprovalDecision
    expected_row_version: int
    cancel_open_command: bool
    actor: str
    reason: str
    correlation_id: str
    created_at_ms: int


class RevokeStore(Protocol):
    """CAS the delivery, clear active approval, and append REVOKE/audit atomically."""

    def load_context(self, delivery_id: str) -> RevokeContext | None: ...
    def apply_revocation(self, write: RevokeWrite) -> None: ...


@dataclass(frozen=True)
class RevokeResult:
    delivery_id: str
    revocation_id: str
    delivery_state: DeliveryState
    row_version: int


_OPEN_COMMAND_STATES = frozenset({"PENDING", "DELIVERING", "ACKED"})


class RevokeApproval:
    def __init__(self, store: RevokeStore, clock: Clock, ids: IdGenerator) -> None:
        self._store = store
        self._clock = clock
        self._ids = ids

    def execute(
        self,
        delivery_id: str,
        *,
        actor: str,
        reason: str,
        correlation_id: str = "application",
    ) -> RevokeResult:
        if not delivery_id.strip() or not actor.strip() or not reason.strip() or not correlation_id.strip():
            raise ValueError("delivery_id, actor, reason and correlation_id are required")
        context = self._store.load_context(delivery_id)
        if context is None:
            raise NotFound("Không tìm thấy bài cần thu hồi.")
        if context.delivery.state not in {DeliveryState.APPROVED, DeliveryState.QUEUED}:
            raise Conflict("Chỉ có thể thu hồi bài đã duyệt hoặc đang chờ đăng.")
        if context.delivery.state is DeliveryState.QUEUED and context.command_state == "AUTHORIZED":
            raise DomainError(ErrorCode.ALREADY_AUTHORIZED, "Lệnh đăng đã được cấp quyền.")
        approval = context.active_approval
        revision_id = context.current_revision.payload.get("revision_id")
        if (
            approval is None
            or approval.decision is not ApprovalType.APPROVE
            or approval.revision_id != revision_id
            or approval.payload_hash != context.current_revision.payload_hash
        ):
            raise Conflict("Approval không khớp revision hiện hành.")
        if context.live_execution:
            raise Conflict("Bài có execution đang hoạt động; không thể thu hồi.")

        now_ms = self._clock.now_ms()
        updated_delivery, _events = context.delivery.apply(
            DeliveryEvent.REVOKE,
            {
                "now_ms": now_ms,
                "no_execution_live": True,
                "command_not_authorized": context.command_state != "AUTHORIZED",
            },
        )
        revocation = ApprovalDecision(
            id=self._ids.new_id(),
            revision_id=approval.revision_id,
            payload_hash=approval.payload_hash,
            decision=ApprovalType.REVOKE,
            actor_id=actor,
            created_at_ms=now_ms,
            reason=reason,
            revokes_id=approval.id,
        )
        self._store.apply_revocation(
            RevokeWrite(
                context=context,
                updated_delivery=updated_delivery,
                revocation=revocation,
                expected_row_version=context.delivery.row_version,
                cancel_open_command=context.command_state in _OPEN_COMMAND_STATES,
                actor=actor,
                reason=reason,
                correlation_id=correlation_id,
                created_at_ms=now_ms,
            )
        )
        return RevokeResult(
            delivery_id=delivery_id,
            revocation_id=revocation.id,
            delivery_state=updated_delivery.state,
            row_version=updated_delivery.row_version,
        )


def revoke_approval(
    use_case: RevokeApproval,
    delivery_id: str,
    *,
    actor: str,
    reason: str,
    correlation_id: str = "application",
) -> RevokeResult:
    return use_case.execute(
        delivery_id, actor=actor, reason=reason, correlation_id=correlation_id
    )
