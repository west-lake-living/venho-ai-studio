from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from growth_engine.application.ports.clock import Clock, IdGenerator
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.states import DeliveryEvent, DeliveryState


class CloseDeliveryTransaction(Protocol):
    def get_delivery(self, delivery_id: str) -> Delivery | None: ...
    def has_live_execution(self, delivery_id: str) -> bool: ...
    def commit_close(
        self,
        delivery: Delivery,
        *,
        updated_delivery: Delivery,
        expected_row_version: int,
        actor_id: str,
        reason: str,
        audit_id: str,
        at_ms: int,
    ) -> bool: ...


class CloseDeliveryStore(Protocol):
    def begin_immediate(self) -> object: ...


@dataclass(frozen=True)
class CloseDeliveryResult:
    delivery_id: str
    state: DeliveryState


class CloseDelivery:
    def __init__(self, store: CloseDeliveryStore, clock: Clock, ids: IdGenerator) -> None:
        self._store = store
        self._clock = clock
        self._ids = ids

    def execute(
        self,
        delivery_id: str,
        *,
        expected_row_version: int,
        actor_id: str,
        reason: str,
    ) -> CloseDeliveryResult:
        if expected_row_version < 1 or not actor_id.strip() or not reason.strip():
            raise ValueError("expected row version, actor and reason are required")
        now_ms = self._clock.now_ms()
        with self._store.begin_immediate() as tx:
            delivery = tx.get_delivery(delivery_id)
            if delivery is None or delivery.state is not DeliveryState.BLOCKED:
                raise ValueError("only a BLOCKED delivery can be closed as failed")
            if delivery.row_version != expected_row_version:
                raise ValueError("delivery changed; reload before closing")
            if tx.has_live_execution(delivery_id):
                raise ValueError("cannot close a delivery with a live execution")
            updated_delivery, _events = delivery.apply(
                DeliveryEvent.MARK_FAILED_FINAL,
                {"now_ms": now_ms, "actor_id": actor_id, "reason": reason},
            )
            if not tx.commit_close(
                delivery,
                updated_delivery=updated_delivery,
                expected_row_version=expected_row_version,
                actor_id=actor_id,
                reason=reason,
                audit_id=self._ids.new_id(),
                at_ms=now_ms,
            ):
                raise ValueError("delivery changed while closing")
            return CloseDeliveryResult(delivery_id, updated_delivery.state)
