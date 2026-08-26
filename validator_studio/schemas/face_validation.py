from __future__ import annotations

from pydantic import BaseModel


class FaceGateResult(BaseModel):
    gate: str
    passed: bool
    reason: str = ""
    evidence: str = ""


class FaceWeightedScores(BaseModel):
    """The fixed 07F scorecard, expressed as required JSON properties.

    A free-form dict produces an object schema that Gemini can satisfy with
    `{}`.  These fields are fixed by the 07F rubric, so making them explicit
    preserves the DTO contract while preventing an empty scorecard.
    """

    facial_shape: float
    eyes_and_brows: float
    nose: float
    mouth_and_chin: float
    technical_quality: float


class FaceValidationObservation(BaseModel):
    gates: list[FaceGateResult]
    weighted_scores: FaceWeightedScores
    notes: list[str] = []
