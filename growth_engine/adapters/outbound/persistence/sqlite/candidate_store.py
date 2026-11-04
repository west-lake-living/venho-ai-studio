from __future__ import annotations

from collections.abc import Callable, Sequence

from growth_engine.application.ports.uow import UnitOfWork
from growth_engine.domain.content.candidate import CandidateState, ResearchCandidate


class SqliteCandidateStore:
    """Transactional application port backed by the file-based SQLite UoW."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def upsert_candidate(
        self,
        candidate: ResearchCandidate,
        *,
        payload_json: str,
        created_at_ms: int,
        actor: str,
        correlation_id: str,
    ) -> tuple[ResearchCandidate, bool]:
        with self._uow_factory().begin_immediate() as tx:
            return tx.candidates.upsert_candidate(
                candidate,
                payload_json=payload_json,
                created_at_ms=created_at_ms,
                actor=actor,
                correlation_id=correlation_id,
            )

    def get_candidate(self, candidate_id: str) -> ResearchCandidate | None:
        with self._uow_factory().read_only() as tx:
            return tx.candidates.get(candidate_id)

    def apply_candidate_decision(
        self,
        candidate_id: str,
        *,
        expected_source_hash: str,
        decision_id: str,
        decision: object,
        next_state: CandidateState,
        actor: str,
        reason: str,
        created_at_ms: int,
        correlation_id: str,
    ) -> ResearchCandidate:
        with self._uow_factory().begin_immediate() as tx:
            return tx.candidates.apply_candidate_decision(
                candidate_id,
                expected_source_hash=expected_source_hash,
                decision_id=decision_id,
                decision=decision,
                next_state=next_state,
                actor=actor,
                reason=reason,
                created_at_ms=created_at_ms,
                correlation_id=correlation_id,
            )

    def expire_due_candidates(
        self,
        now_ms: int,
        *,
        actor: str,
        correlation_id: str,
    ) -> Sequence[str]:
        with self._uow_factory().begin_immediate() as tx:
            return tx.candidates.expire_due_candidates(
                now_ms,
                actor=actor,
                correlation_id=correlation_id,
            )
