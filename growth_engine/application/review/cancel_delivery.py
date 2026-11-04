from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from growth_engine.application.errors import Conflict, NotFound
from growth_engine.application.ports.clock import Clock
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.states import DeliveryEvent, DeliveryState
from growth_engine.domain.kernel.errors import DomainError, ErrorCode


@dataclass(frozen=True)
class CancelContext:
    delivery: Delivery
    command_state: str | None
    live_execution: bool


@dataclass(frozen=True)
class CancelWrite:
    context: CancelContext
    updated_delivery: Delivery
    expected_row_version: int
    cancel_open_command: bool
    actor: str
    reason: str
    correlation_id: str
    cancelled_at_ms: int


class CancelStore(Protocol):
    """CAS delivery, cancel any open command, and append audit in one transaction."""

    def load_context(self, delivery_id: str) -> CancelContext | None: ...
    def apply_cancellation(self, write: CancelWrite) -> None: ...


@dataclass(frozen=True)
class CancelResult:
    delivery_id: str
    delivery_state: DeliveryState
    row_version: int


_CANCELLABLE = frozenset(
    {
        DeliveryState.DRAFT,
        DeliveryState.IN_REVIEW,
        DeliveryState.APPROVED,
        DeliveryState.QUEUED,
        DeliveryState.BLOCKED,
    }
)
_OPEN_COMMAND_STATES = frozenset({"PENDING", "DELIVERING", "ACKED"})


class CancelDelivery:
    def __init__(self, store: CancelStore, clock: Clock) -> None:
        self._store = store
        self._clock = clock

    def execute(
        self,
        delivery_id: str,
        *,
        actor: str,
        reason: str,
        correlation_id: str = "application",
    ) -> CancelResult:
        if not delivery_id.strip() or not actor.strip() or not reason.strip() or not correlation_id.strip():
            raise ValueError("delivery_id, actor, reason and correlation_id are required")
        context = self._store.load_context(delivery_id)
        if context is None:
            raise NotFound("Không tìm thấy bài cần huỷ.")
        if context.delivery.state not in _CANCELLABLE:
            raise Conflict("Trạng thái bài không cho phép huỷ.")
        if context.delivery.state is DeliveryState.QUEUED and context.command_state == "AUTHORIZED":
            raise DomainError(ErrorCode.ALREADY_AUTHORIZED, "Lệnh đăng đã được cấp quyền.")
        if context.live_execution:
            raise Conflict("Bài có execution đang hoạt động; không thể huỷ.")

        now_ms = self._clock.now_ms()
        updated_delivery, _events = context.delivery.apply(
            DeliveryEvent.CANCEL,
            {
                "now_ms": now_ms,
                "no_execution_live": True,
                "command_not_authorized": context.command_state != "AUTHORIZED",
                "reason": reason,
            },
        )
        self._store.apply_cancellation(
            CancelWrite(
                context=context,
                updated_delivery=updated_delivery,
                expected_row_version=context.delivery.row_version,
                cancel_open_command=context.command_state in _OPEN_COMMAND_STATES,
                actor=actor,
                reason=reason,
                correlation_id=correlation_id,
                cancelled_at_ms=now_ms,
            )
        )
        return CancelResult(delivery_id, updated_delivery.state, updated_delivery.row_version)


def cancel_delivery(
    use_case: CancelDelivery,
    delivery_id: str,
    *,
    actor: str,
    reason: str,
    correlation_id: str = "application",
) -> CancelResult:
    return use_case.execute(
        delivery_id, actor=actor, reason=reason, correlation_id=correlation_id
    )
