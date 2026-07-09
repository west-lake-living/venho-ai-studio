from __future__ import annotations

from pydantic import BaseModel


class FaceGateResult(BaseModel):
    gate: str
    passed: bool
    reason: str = ""
    evidence: str = ""


class FaceValidationObservation(BaseModel):
    gates: list[FaceGateResult]
    weighted_scores: dict[str, float] = {}
    notes: list[str] = []
