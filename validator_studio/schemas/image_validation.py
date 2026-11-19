from __future__ import annotations

from pydantic import BaseModel, Field

from validator_studio.schemas.validation_base import MatchState, Severity


class DnaMatchObservation(BaseModel):
    key: str
    expected: str = ""
    observed: str = ""
    category: str = "dna_match"
    match_state: MatchState
    confidence_bp: int = Field(default=10_000, ge=0, le=10_000)
    reason: str = ""
    evidence: str = ""


class ForbiddenObservation(BaseModel):
    rule: str
    source: str = "curated"
    severity: Severity = Severity.HIGH
    violated: bool = False
    confidence_bp: int = Field(default=10_000, ge=0, le=10_000)
    reason: str = ""


class AllowedImperfectionObservation(BaseModel):
    item: str
    present: bool = False
    reason: str = ""


class ImageObservation(BaseModel):
    dna_matches: list[DnaMatchObservation]
    forbidden: list[ForbiddenObservation] = []
    allowed_imperfections: list[AllowedImperfectionObservation] = []
    notes: list[str] = []

