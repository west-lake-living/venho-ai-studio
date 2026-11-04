from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Protocol

from growth_engine.application.errors import ApplicationError, Conflict, NotFound
from growth_engine.application.ports.clock import Clock, IdGenerator
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.states import DeliveryEvent, DeliveryState
from growth_engine.domain.delivery.transitions import apply_transition
from growth_engine.domain.kernel.errors import DomainError, ErrorCode
from growth_engine.domain.kernel.hashing import canonical_json_bytes, sha256_hex
from growth_engine.domain.scheduling.slot import Slot, SlotTarget


class TargetAlreadyReserved(ApplicationError):
    code = "ERR_GC2_TARGET_TAKEN"


class ReserveTargetTransaction(Protocol):
    def load_target_context(self, target_id: str) -> dict[str, object] | None: ...
    def insert_draft_delivery(
        self,
        delivery: Delivery,
        *,
        target: SlotTarget,
        package_id: str,
        created_at_ms: int,
    ) -> bool: ...
    def append_audit(self, **entry: object) -> None: ...


class ReserveTargetStore(Protocol):
    def begin_immediate(self) -> AbstractContextManager[ReserveTargetTransaction]: ...


class ReserveTarget:
    """Reserve one target using D01 with a transaction-wide active-delivery guard."""

    def __init__(self, store: ReserveTargetStore, clock: Clock, ids: IdGenerator) -> None:
        self._store = store
        self._clock = clock
        self._ids = ids

    def execute(
        self,
        target_id: str,
        *,
        package_id: str,
        lane: str,
        correlation_id: str,
    ) -> Delivery:
        if not target_id.strip() or not package_id.strip() or not lane.strip() or not correlation_id.strip():
            raise ValueError("target_id, package_id, lane and correlation_id are required")
        now_ms = self._clock.now_ms()
        with self._store.begin_immediate() as tx:
            context = tx.load_target_context(target_id)
            if context is None:
                raise NotFound("Không tìm thấy target cần đặt chỗ.")
            target = context.get("target")
            slot = context.get("slot")
            active_delivery = context.get("active_delivery")
            if not isinstance(target, SlotTarget) or not isinstance(slot, Slot):
                raise ValueError("target context must include a SlotTarget and Slot")
            if target.id != target_id or target.slot_id != slot.id:
                raise ValueError("target context identity does not match the requested target")
            if slot.cancelled_at_ms is not None:
                raise Conflict("Không thể tạo delivery cho slot đã huỷ.")
            if slot.lane != lane:
                raise Conflict("Lane của package không khớp lane của slot.")
            if isinstance(active_delivery, Delivery) and active_delivery.active:
                raise _target_taken(active_delivery.id)
            if active_delivery is not None and not isinstance(active_delivery, Delivery):
                raise ValueError("active_delivery must be a Delivery or None")

            delivery_id = self._ids.new_id()
            state = apply_transition(
                None,
                DeliveryEvent.RESERVE,
                {"target_available": True, "slot_not_cancelled": True},
            )
            if state is not DeliveryState.DRAFT:
                raise DomainError(ErrorCode.STATE_CONFLICT, "Target không thể chuyển sang DRAFT.")
            delivery = Delivery(id=delivery_id, state=state)
            if not tx.insert_draft_delivery(
                delivery,
                target=target,
                package_id=package_id,
                created_at_ms=now_ms,
            ):
                latest = tx.load_target_context(target_id)
                winner = None if latest is None else latest.get("active_delivery")
                raise _target_taken(winner.id if isinstance(winner, Delivery) else None)
            tx.append_audit(
                aggregate_type="delivery",
                aggregate_id=delivery.id,
                actor="growth-engine",
                action="reserve_target",
                before_hash=None,
                after_hash=sha256_hex(
                    canonical_json_bytes(
                        {
                            "id": delivery.id,
                            "target_id": target.id,
                            "package_id": package_id,
                            "state": delivery.state.value,
                        }
                    )
                ),
                details={"target_id": target.id, "package_id": package_id},
                correlation_id=correlation_id,
                created_at_ms=now_ms,
            )
            return delivery


def _target_taken(existing_delivery_id: str | None) -> TargetAlreadyReserved:
    details = {"existing_delivery_id": existing_delivery_id} if existing_delivery_id else {}
    return TargetAlreadyReserved("Target đã có delivery active.", details)
