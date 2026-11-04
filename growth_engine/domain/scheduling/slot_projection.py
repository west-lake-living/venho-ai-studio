from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from growth_engine.domain.delivery.states import LIVE, DeliveryState
from growth_engine.domain.scheduling.slot import Slot, SlotTarget


class SlotViewState(str, Enum):
    CANCELLED = "CANCELLED"
    NEEDS_ATTENTION = "NEEDS_ATTENTION"
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    MISSED = "MISSED"
    READY = "READY"
    AWAITING_REVIEW = "AWAITING_REVIEW"
    PLANNED = "PLANNED"


@dataclass(frozen=True)
class DeliveryProgress:
    target_id: str
    state: DeliveryState
    quality: str | None = None
    reported_at_ms: int | None = None


@dataclass(frozen=True)
class SlotProjection:
    state: SlotViewState
    published: int
    total: int
    attention_flags: tuple[str, ...] = ()

    @property
    def progress(self) -> dict[str, int]:
        return {"published": self.published, "total": self.total}


def derive_slot_view(
    slot: Slot,
    targets: Sequence[SlotTarget],
    deliveries: Sequence[DeliveryProgress],
    *,
    now_ms: int,
) -> SlotProjection:
    if type(now_ms) is not int:
        raise ValueError("now_ms must be integer epoch milliseconds")
    target_by_id = {target.id: target for target in targets}
    if len(target_by_id) != len(targets):
        raise ValueError("duplicate slot target")
    if any(target.slot_id != slot.id for target in targets):
        raise ValueError("slot target belongs to another slot")
    delivery_by_target = {delivery.target_id: delivery for delivery in deliveries}
    if len(delivery_by_target) != len(deliveries):
        raise ValueError("duplicate delivery for target")
    if any(target_id not in target_by_id for target_id in delivery_by_target):
        raise ValueError("delivery references an unknown slot target")

    required = [target for target in targets if target.required]
    published = sum(
        delivery_by_target.get(target.id) is not None
        and delivery_by_target[target.id].state is DeliveryState.PUBLISHED
        for target in required
    )
    view = lambda state, flags=(): SlotProjection(state, published, len(required), tuple(flags))

    if slot.cancelled_at_ms is not None:
        return view(SlotViewState.CANCELLED)

    attention_flags: list[str] = []
    for target in targets:
        delivery = delivery_by_target.get(target.id)
        if delivery is None:
            continue
        prefix = target.channel_id.upper()
        if delivery.state in {
            DeliveryState.UNKNOWN,
            DeliveryState.BLOCKED,
            DeliveryState.FAILED_FINAL,
        }:
            attention_flags.append(f"{prefix}_{delivery.state.value}")
        if delivery.quality == "FAIL":
            attention_flags.append(f"{prefix}_QUALITY_FAIL")
        if (
            delivery.state is DeliveryState.REPORTED_PUBLISHED
            and delivery.reported_at_ms is not None
            and now_ms - delivery.reported_at_ms > 60 * 60_000
        ):
            attention_flags.append(f"{prefix}_VERIFY_OVERDUE")
    if attention_flags:
        return view(SlotViewState.NEEDS_ATTENTION, attention_flags)

    required_states = [
        delivery_by_target[target.id].state
        for target in required
        if target.id in delivery_by_target
    ]
    if required and len(required_states) == len(required) and all(
        state is DeliveryState.PUBLISHED for state in required_states
    ):
        return view(SlotViewState.COMPLETE)

    has_post = any(
        delivery.state in {DeliveryState.PUBLISHED, DeliveryState.REPORTED_PUBLISHED}
        for delivery in delivery_by_target.values()
    )
    unfinished_required = any(
        target.id not in delivery_by_target
        or delivery_by_target[target.id].state is not DeliveryState.PUBLISHED
        for target in required
    )
    if has_post and unfinished_required:
        return view(SlotViewState.PARTIAL)

    has_live_execution = any(delivery.state in LIVE for delivery in delivery_by_target.values())
    if now_ms > slot.deadline_at_ms and not has_post and not has_live_execution:
        return view(SlotViewState.MISSED)

    ready_states = {DeliveryState.APPROVED, DeliveryState.QUEUED, DeliveryState.EXECUTING}
    remaining = [state for state in required_states if state is not DeliveryState.PUBLISHED]
    all_required_resolved = len(required_states) == len(required)
    if required and all_required_resolved and remaining and all(state in ready_states for state in remaining):
        return view(SlotViewState.READY)

    if any(
        delivery.state is DeliveryState.IN_REVIEW
        for delivery in delivery_by_target.values()
    ):
        return view(SlotViewState.AWAITING_REVIEW)
    return view(SlotViewState.PLANNED)
