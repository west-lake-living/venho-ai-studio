from __future__ import annotations

from collections.abc import Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Protocol

from growth_engine.application.ports.clock import IdGenerator
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.states import DeliveryEvent
from growth_engine.domain.kernel.errors import DomainError


@dataclass(frozen=True)
class ExpireCandidate:
    delivery: Delivery
    deadline_at_ms: int
    has_live_execution: bool

    def __post_init__(self) -> None:
        if type(self.deadline_at_ms) is not int or self.deadline_at_ms < 0:
            raise ValueError("deadline_at_ms must be a non-negative integer")
        if type(self.has_live_execution) is not bool:
            raise ValueError("has_live_execution must be a boolean")


@dataclass(frozen=True)
class ExpireOverdueResult:
    expired_delivery_ids: tuple[str, ...] = ()
    skipped_delivery_ids: tuple[str, ...] = ()


class ExpireTransaction(Protocol):
    def get_expire_candidate(self, delivery_id: str) -> ExpireCandidate | None: ...

    def commit_expire(
        self,
        candidate: ExpireCandidate,
        updated_delivery: Delivery,
        *,
        expected_row_version: int,
        at_ms: int,
        audit_event_id: str,
        correlation_id: str,
    ) -> bool: ...


class ExpireOverdueStore(Protocol):
    def overdue_delivery_ids(self, now_ms: int) -> Sequence[str]: ...
    def begin_immediate(self) -> AbstractContextManager[ExpireTransaction]: ...


class ExpireOverdue:
    """Apply D21 to expired deliveries, closing any open publish command atomically."""

    def __init__(self, store: ExpireOverdueStore, ids: IdGenerator) -> None:
        self._store = store
        self._ids = ids

    def execute(self, now_ms: int) -> ExpireOverdueResult:
        if type(now_ms) is not int or now_ms < 0:
            raise ValueError("now_ms must be a non-negative integer")
        delivery_ids = tuple(dict.fromkeys(self._store.overdue_delivery_ids(now_ms)))
        expired: list[str] = []
        skipped: list[str] = []
        for delivery_id in delivery_ids:
            if not isinstance(delivery_id, str) or not delivery_id.strip():
                raise ValueError("overdue_delivery_ids must return non-empty delivery ids")
            with self._store.begin_immediate() as tx:
                candidate = tx.get_expire_candidate(delivery_id)
                if candidate is None or candidate.has_live_execution or now_ms <= candidate.deadline_at_ms:
                    skipped.append(delivery_id)
                    continue
                try:
                    updated_delivery, _events = candidate.delivery.apply(
                        DeliveryEvent.EXPIRE,
                        {
                            "now_ms": now_ms,
                            "deadline_at_ms": candidate.deadline_at_ms,
                            "no_execution_live": not candidate.has_live_execution,
                        },
                    )
                except DomainError:
                    skipped.append(delivery_id)
                    continue
                committed = tx.commit_expire(
                    candidate,
                    updated_delivery,
                    expected_row_version=candidate.delivery.row_version,
                    at_ms=now_ms,
                    audit_event_id=self._ids.new_id(),
                    correlation_id=f"publish-expire:{candidate.delivery.id}:{now_ms}",
                )
                if committed:
                    expired.append(candidate.delivery.id)
                else:
                    skipped.append(candidate.delivery.id)
        return ExpireOverdueResult(tuple(expired), tuple(skipped))
