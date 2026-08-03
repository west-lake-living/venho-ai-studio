from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional


class TrendCandidate(BaseModel):
    id: str
    title: str
    source_uri: str
    geographic: str
    thematic: str
    actionability: str
    brand_safety_category: str
    intersections: list[str] = Field(default_factory=list)
    relevance_score: float = 0.0
    status: str = "candidate"
    rejection_reason: Optional[str] = None
