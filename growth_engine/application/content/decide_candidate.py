from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from growth_engine.application.errors import Conflict, NotFound
from growth_engine.application.ports.clock import Clock, IdGenerator
from growth_engine.domain.content.candidate import CandidateState, ResearchCandidate


class CandidateDecisionKind(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


@dataclass(frozen=True)
class DecideCandidateCommand:
    candidate_id: str
    source_hash: str
    decision: CandidateDecisionKind
    actor: str
    reason: str = ""
    correlation_id: str = "candidate-decision"


@dataclass(frozen=True)
class DecideCandidateResult:
    candidate: ResearchCandidate
    decision_id: str


class CandidateDecisionStore(Protocol):
    def get_candidate(self, candidate_id: str) -> ResearchCandidate | None: ...
    def apply_candidate_decision(
        self,
        candidate_id: str,
        *,
        expected_source_hash: str,
        decision_id: str,
        decision: CandidateDecisionKind,
        next_state: CandidateState,
        actor: str,
        reason: str,
        created_at_ms: int,
        correlation_id: str,
    ) -> ResearchCandidate: ...


class DecideCandidate:
    """Record a human decision against one immutable source revision."""

    def __init__(self, store: CandidateDecisionStore, clock: Clock, ids: IdGenerator) -> None:
        self._store = store
        self._clock = clock
        self._ids = ids

    def execute(self, command: DecideCandidateCommand) -> DecideCandidateResult:
        if not command.candidate_id.strip() or not command.source_hash.strip():
            raise ValueError("candidate_id and source_hash are required")
        if not command.actor.strip() or not command.correlation_id.strip():
            raise ValueError("actor and correlation_id are required")
        if not isinstance(command.decision, CandidateDecisionKind):
            raise ValueError("decision must be CandidateDecisionKind")
        candidate = self._store.get_candidate(command.candidate_id)
        if candidate is None:
            raise NotFound("Không tìm thấy research candidate.")
        now_ms = self._clock.now_ms()
        if candidate.source_hash != command.source_hash:
            raise Conflict("Nguồn candidate đã đổi; hãy tải lại trước khi quyết định.")
        if candidate.state is not CandidateState.NEW:
            raise Conflict("Chỉ candidate NEW mới nhận quyết định.")
        if now_ms >= candidate.expires_at_ms or (
            candidate.event_end_at_ms is not None and now_ms >= candidate.event_end_at_ms
        ):
            raise Conflict("Research candidate đã hết hạn.")
        next_state = (
            CandidateState.APPROVED
            if command.decision is CandidateDecisionKind.APPROVE
            else CandidateState.REJECTED
        )
        decision_id = self._ids.new_id()
        updated = self._store.apply_candidate_decision(
            candidate.id,
            expected_source_hash=candidate.source_hash,
            decision_id=decision_id,
            decision=command.decision,
            next_state=next_state,
            actor=command.actor,
            reason=command.reason,
            created_at_ms=now_ms,
            correlation_id=command.correlation_id,
        )
        return DecideCandidateResult(updated, decision_id)
