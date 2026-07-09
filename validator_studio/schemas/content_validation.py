from __future__ import annotations

from pydantic import BaseModel


class ContentQualityObservation(BaseModel):
    brand_fit: float
    tone: float
    clarity: float
    cta: float
    language_fit: float
    production_readiness: float
    notes: list[str] = []
