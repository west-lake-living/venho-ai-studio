from __future__ import annotations

from datetime import date
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from research_engine.domain.evidence_level import EvidenceLevel


ResearchType = Literal["source", "note", "synthesis", "insight", "event", "trend"]
ResearchDomain = Literal[
    "guest_voice",
    "competitor",
    "local_intel",
    "platform_trend",
    "brand_visual",
    "market_pricing",
    "social_trend",
    "local_events",
]
ResearchStatus = Literal["draft", "reviewed", "promoted", "archived"]


class ResearchNote(BaseModel):
    model_config = ConfigDict(extra="allow")

    rs_id: str
    type: ResearchType
    domain: ResearchDomain
    evidence_level: EvidenceLevel
    status: ResearchStatus = "draft"
    collected_at: date
    source_uri: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    expires_at: Optional[date] = None
    promoted_fact_keys: list[str] = Field(default_factory=list)
    related_briefs: list[str] = Field(default_factory=list)
    verified_by_human: bool = False
    tags: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def enforce_research_invariants(self) -> "ResearchNote":
        if self.type == "source" and not self.source_uri:
            raise ValueError("source_uri is required for source notes")
        if self.evidence_level.requires_expiry and self.expires_at is None:
            raise ValueError("R2 and R2-T notes require expires_at")
        if self.type == "event":
            event_fields = {**(self.model_extra or {}), **self.extra}
            missing = [key for key in ("event_name", "event_start", "event_end", "venue") if key not in event_fields]
            if missing:
                raise ValueError(f"event note missing: {', '.join(missing)}")
        return self

    @property
    def can_be_claim_source(self) -> bool:
        return self.evidence_level.citable and self.status == "promoted"
