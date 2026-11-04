from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from growth_engine.application.ports.clock import Clock


@dataclass(frozen=True)
class ExpireCandidatesResult:
    expired_candidate_ids: tuple[str, ...]


class ExpireCandidatesStore(Protocol):
    def expire_due_candidates(
        self,
        now_ms: int,
        *,
        actor: str,
        correlation_id: str,
    ) -> Sequence[str]:
        """Atomically expire due NEW/APPROVED rows and append their audit events."""


class ExpireCandidates:
    def __init__(self, store: ExpireCandidatesStore, clock: Clock) -> None:
        self._store = store
        self._clock = clock

    def execute(self) -> ExpireCandidatesResult:
        now_ms = self._clock.now_ms()
        expired = self._store.expire_due_candidates(
            now_ms,
            actor="growth-engine",
            correlation_id=f"expire-candidates:{now_ms}",
        )
        return ExpireCandidatesResult(tuple(expired))
