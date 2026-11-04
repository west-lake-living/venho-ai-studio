from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping

from growth_engine.domain.delivery.states import DeliveryEvent, DeliveryState
from growth_engine.domain.delivery.transitions import apply_transition
from growth_engine.domain.kernel.events import DomainEvent


@dataclass(frozen=True)
class Delivery:
    id: str
    state: DeliveryState
    row_version: int = 1
    permalink: str | None = None

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("delivery id must not be empty")
        if type(self.row_version) is not int or self.row_version < 1:
            raise ValueError("row_version must be a positive integer")

    @property
    def active(self) -> bool:
        return self.state is not DeliveryState.SUPERSEDED

    def apply(
        self,
        event: DeliveryEvent,
        ctx: Mapping[str, object] | None = None,
    ) -> tuple[Delivery, list[DomainEvent]]:
        context = ctx or {}
        at_ms = context.get("now_ms", context.get("at_ms"))
        if type(at_ms) is not int:
            raise ValueError("ctx must include integer now_ms or at_ms")
        target = apply_transition(self.state, event, context)
        updated = replace(self, state=target, row_version=self.row_version + 1)
        domain_event = DomainEvent(
            name="DELIVERY_STATE_CHANGED",
            aggregate_id=self.id,
            at_ms=at_ms,
            data={
                "event": event.value,
                "from_state": self.state.value,
                "to_state": target.value,
                "row_version": updated.row_version,
            },
        )
        return updated, [domain_event]
