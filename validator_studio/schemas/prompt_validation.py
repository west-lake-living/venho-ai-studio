from __future__ import annotations

from pydantic import BaseModel


class PromptQualityObservation(BaseModel):
    dna_coverage: float
    forbidden_conflict: float
    clarity: float
    token_efficiency: float
    output_specificity: float
    production_readiness: float
    notes: list[str] = []

