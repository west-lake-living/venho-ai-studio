from __future__ import annotations

from dataclasses import dataclass

from research_engine.domain.evidence_level import EvidenceLevel, can_transition
from research_engine.domain.research_note import ResearchNote


@dataclass(frozen=True)
class PromotionDecision:
    allowed: bool
    reason: str


class PromotionPolicy:
    def __init__(self, min_confidence: float = 0.8) -> None:
        self.min_confidence = min_confidence

    def evaluate(self, note: ResearchNote, *, human_approved: bool) -> PromotionDecision:
        if note.evidence_level is EvidenceLevel.R2_T:
            return PromotionDecision(False, "R2-T is context-only and cannot become R3")
        if note.evidence_level is not EvidenceLevel.R2:
            return PromotionDecision(False, "Only R2 synthesis/insight notes can be promoted")
        if note.confidence < self.min_confidence:
            return PromotionDecision(False, "Confidence below promotion threshold")
        if not can_transition(note.evidence_level, EvidenceLevel.R3, human_approved=human_approved):
            return PromotionDecision(False, "Founder approval is required")
        return PromotionDecision(True, "Ready for approved KnowledgeFact creation")
