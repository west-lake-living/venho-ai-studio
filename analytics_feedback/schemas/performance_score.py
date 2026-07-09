from __future__ import annotations

from typing import Dict, List, Literal

from pydantic import BaseModel, Field


PerformanceLabel = Literal["OUTPERFORM", "NORMAL", "UNDERPERFORM", "INSUFFICIENT_DATA"]
Confidence = Literal["low", "medium", "high"]


class PerformanceScore(BaseModel):
    contract_version: str = "1.0"
    snapshot_id: str
    package_id: str
    platform: str
    score_timestamp_utc: str
    baseline_group: Dict[str, str]
    sample_size: int
    performance_label: PerformanceLabel
    relative_score: float
    confidence: Confidence
    reasons: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
