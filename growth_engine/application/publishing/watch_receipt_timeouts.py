from __future__ import annotations

from collections.abc import Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Protocol

from growth_engine.application.ports.clock import Clock, IdGenerator
from growth_engine.application.publishing.apply_receipt import ReceiptApplySnapshot
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.states import DeliveryEvent, DeliveryState
from growth_engine.domain.publishing.execution import Execution, ExecutionState


class ReceiptTimeoutTransaction(Protocol):
    def list_due_receipt_timeouts(self, now_ms: int, limit: int) -> Sequence[ReceiptApplySnapshot]: ...

    def commit_timeout(
        self,
        candidate: ReceiptApplySnapshot,
        *,
        execution: Execution,
        delivery: Delivery,
        incident: dict[str, object],
        audit_id: str,
        correlation_id: str,
        at_ms: int,
    ) -> bool: ...


class ReceiptTimeoutStore(Protocol):
    def begin_immediate(self) -> AbstractContextManager[ReceiptTimeoutTransaction]: ...


@dataclass(frozen=True)
class WatchReceiptTimeoutsResult:
    timed_out: int
    execution_ids: tuple[str, ...]


class WatchReceiptTimeouts:
    """Move overdue AUTHORIZED executions to UNKNOWN exactly once."""

    def __init__(
        self,
        store: ReceiptTimeoutStore,
        clock: Clock,
        ids: IdGenerator,
        *,
        batch_size: int = 100,
    ) -> None:
        if type(batch_size) is not int or batch_size < 1:
            raise ValueError("batch_size must be a positive integer")
        self._store = store
        self._clock = clock
        self._ids = ids
        self._batch_size = batch_size

    def execute(self) -> WatchReceiptTimeoutsResult:
        now_ms = self._clock.now_ms()
        timed_out: list[str] = []
        with self._store.begin_immediate() as tx:
            candidates = tx.list_due_receipt_timeouts(now_ms, self._batch_size)
            for candidate in candidates:
                execution = candidate.execution
                delivery = candidate.delivery
                if (
                    execution is None
                    or delivery is None
                    or execution.state is not ExecutionState.AUTHORIZED
                    or delivery.state is not DeliveryState.EXECUTING
                    or now_ms <= execution.receipt_due_at_ms
                ):
                    continue
                updated_execution = execution.timeout(now_ms=now_ms)
                updated_delivery, _events = delivery.apply(
                    DeliveryEvent.RECEIPT_TIMEOUT,
                    {"now_ms": now_ms},
                )
                incident = {
                    "incident_type": "UNKNOWN",
                    "channel_id": candidate.channel_id or None,
                    "ref": delivery.id,
                    "severity": "HIGH",
                    "details": {
                        "execution_id": execution.id,
                        "receipt_due_at_ms": execution.receipt_due_at_ms,
                        "timed_out_at_ms": now_ms,
                    },
                    "incident_id": self._ids.new_id(),
                    "at_ms": now_ms,
                }
                committed = tx.commit_timeout(
                    candidate,
                    execution=updated_execution,
                    delivery=updated_delivery,
                    incident=incident,
                    audit_id=self._ids.new_id(),
                    correlation_id="receipt-timeout-watch",
                    at_ms=now_ms,
                )
                if committed:
                    timed_out.append(execution.id)
        return WatchReceiptTimeoutsResult(len(timed_out), tuple(timed_out))
