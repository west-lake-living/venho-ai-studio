from __future__ import annotations

from enum import Enum
from typing import Dict, Mapping, Optional

from pydantic import BaseModel, Field


class ValidationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNVALIDATED = "UNVALIDATED"


class RegionValidation(BaseModel):
    region: str
    status: ValidationStatus
    score: Optional[float] = Field(default=None, ge=0, le=100)
    threshold: Optional[float] = Field(default=None, ge=0, le=100)
    reason: Optional[str] = None


class RegionalValidator:
    """Scores each region independently; no full-frame identity gate."""

    def __init__(self, *, identity_threshold: float = 90.0, geometry_threshold: float = 92.0) -> None:
        self.identity_threshold = identity_threshold
        self.geometry_threshold = geometry_threshold

    def validate(self, scores: Mapping[str, Optional[float]]) -> Dict[str, RegionValidation]:
        thresholds = {
            "identity": self.identity_threshold,
            "facial_geometry": self.geometry_threshold,
        }
        result: Dict[str, RegionValidation] = {}
        for region, score in scores.items():
            threshold = thresholds.get(region)
            if score is None:
                result[region] = RegionValidation(region=region, status=ValidationStatus.UNVALIDATED,
                                                  threshold=threshold, reason="score_missing")
            elif threshold is None:
                result[region] = RegionValidation(region=region, status=ValidationStatus.PASS,
                                                  score=score, reason="informational_region")
            else:
                result[region] = RegionValidation(region=region,
                                                  status=ValidationStatus.PASS if score >= threshold else ValidationStatus.FAIL,
                                                  score=score, threshold=threshold,
                                                  reason=None if score >= threshold else "below_threshold")
        return result

    @staticmethod
    def overall_status(results: Mapping[str, RegionValidation]) -> ValidationStatus:
        if any(item.status == ValidationStatus.FAIL for item in results.values()):
            return ValidationStatus.FAIL
        if any(item.status == ValidationStatus.UNVALIDATED for item in results.values()):
            return ValidationStatus.UNVALIDATED
        return ValidationStatus.PASS
