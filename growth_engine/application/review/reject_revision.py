from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from growth_engine.application.errors import Conflict, NotFound
from growth_engine.application.ports.clock import Clock, IdGenerator
from growth_engine.domain.delivery.approval import ApprovalDecision, ApprovalType
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.revision import DeliveryRevision
from growth_engine.domain.delivery.states import DeliveryEvent, DeliveryState


class ReplaceMode(str, Enum):
    NONE = "NONE"
    REVISE = "REVISE"
    NEW_TOPIC = "NEW_TOPIC"


@dataclass(frozen=True)
class RejectContext:
    delivery: Delivery
    current_revision: DeliveryRevision
    current_revision_id: str
    live_execution: bool


@dataclass(frozen=True)
class RejectionWrite:
    context: RejectContext
    updated_delivery: Delivery
    decision: ApprovalDecision
    replace_mode: ReplaceMode
    expected_revision_id: str
    job_id: str | None
    job_kind: str | None
    replacement_delivery_id: str | None
    actor: str
    correlation_id: str
    created_at_ms: int


class RejectionStore(Protocol):
    """CAS the delivery and apply rejection/replacement atomically with audit.

    NEW_TOPIC supersedes the old delivery and creates a DRAFT on the same target in
    this transaction (D23); REVISE/NEW_TOPIC enqueue their job in this transaction.
    """

    def load_context(self, delivery_id: str) -> RejectContext | None: ...
    def apply_rejection(self, write: RejectionWrite) -> None: ...


@dataclass(frozen=True)
class RejectResult:
    delivery_id: str
    revision_id: str
    decision: ApprovalDecision
    delivery_state: DeliveryState
    row_version: int
    replacement_delivery_id: str | None


class RejectRevision:
    def __init__(self, store: RejectionStore, clock: Clock, ids: IdGenerator) -> None:
        self._store = store
        self._clock = clock
        self._ids = ids

    def execute(
        self,
        delivery_id: str,
        *,
        revision_id: str,
        reason: str,
        replace_mode: ReplaceMode,
        actor: str,
        correlation_id: str = "application",
    ) -> RejectResult:
        if not delivery_id.strip() or not revision_id.strip():
            raise ValueError("delivery_id and revision_id are required")
        if not reason.strip() or not actor.strip() or not correlation_id.strip():
            raise ValueError("reason, actor and correlation_id are required")
        if not isinstance(replace_mode, ReplaceMode):
            raise ValueError("replace_mode must be a ReplaceMode")
        context = self._store.load_context(delivery_id)
        if context is None:
            raise NotFound("Không tìm thấy bài cần từ chối.")
        if context.delivery.state is not DeliveryState.IN_REVIEW:
            raise Conflict("Chỉ có thể từ chối bài đang chờ duyệt.")
        if revision_id != context.current_revision_id:
            raise Conflict("Revision cần từ chối không còn là revision hiện hành.")
        if context.current_revision.payload.get("revision_id") != revision_id:
            raise Conflict("Dữ liệu revision không khớp delivery.")
        if context.live_execution:
            raise Conflict("Bài có execution đang hoạt động.")

        now_ms = self._clock.now_ms()
        event = DeliveryEvent.SUPERSEDE if replace_mode is ReplaceMode.NEW_TOPIC else DeliveryEvent.REJECT
        transition_context = (
            {"no_execution_live": False} if context.live_execution else
            {"no_execution_live": True} if event is DeliveryEvent.SUPERSEDE else
            {"revision_is_current": True}
        )
        updated_delivery, _events = context.delivery.apply(event, {"now_ms": now_ms, **transition_context})
        decision = ApprovalDecision(
            id=self._ids.new_id(),
            revision_id=revision_id,
            payload_hash=context.current_revision.payload_hash,
            decision=ApprovalType.REJECT,
            actor_id=actor,
            created_at_ms=now_ms,
            reason=reason,
        )
        job_kind = {
            ReplaceMode.NONE: None,
            ReplaceMode.REVISE: "revise",
            ReplaceMode.NEW_TOPIC: "new_topic",
        }[replace_mode]
        job_id = self._ids.new_id() if job_kind else None
        replacement_delivery_id = (
            self._ids.new_id() if replace_mode is ReplaceMode.NEW_TOPIC else None
        )
        write = RejectionWrite(
            context=context,
            updated_delivery=updated_delivery,
            decision=decision,
            replace_mode=replace_mode,
            expected_revision_id=revision_id,
            job_id=job_id,
            job_kind=job_kind,
            replacement_delivery_id=replacement_delivery_id,
            actor=actor,
            correlation_id=correlation_id,
            created_at_ms=now_ms,
        )
        self._store.apply_rejection(write)
        return RejectResult(
            delivery_id=delivery_id,
            revision_id=revision_id,
            decision=decision,
            delivery_state=updated_delivery.state,
            row_version=updated_delivery.row_version,
            replacement_delivery_id=replacement_delivery_id,
        )


def reject_revision(
    use_case: RejectRevision,
    delivery_id: str,
    *,
    revision_id: str,
    reason: str,
    replace_mode: ReplaceMode,
    actor: str,
    correlation_id: str = "application",
) -> RejectResult:
    return use_case.execute(
        delivery_id,
        revision_id=revision_id,
        reason=reason,
        replace_mode=replace_mode,
        actor=actor,
        correlation_id=correlation_id,
    )
