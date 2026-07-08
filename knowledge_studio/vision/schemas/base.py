from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, model_validator

CONTRACT_VERSION = "1.1"


class ObservedFeature(BaseModel):
    key: str
    type: Literal["enum", "free"] = "free"
    value: str
    category: str
    confidence: float = Field(ge=0.0, le=1.0)


class BaseObservation(BaseModel):
    contract_version: str = "1.0"  # observations stay at 1.0 — only DNA bumped to 1.1
    mode: Literal["A", "B"] = "B"
    image_hash: str
    image_file: str
    subject: str
    schema_id: str = "universal"
    schema_version: str
    prompt_version: str
    provider: str = ""
    model: str = ""
    observed_at: str
    features: list[ObservedFeature]
    notable_features: list[str] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)
    forbidden_hints: list[str] = Field(default_factory=list)


# --- DNA output types ---

class InvariantFeature(BaseModel):
    key: str
    value: str
    value_source: Literal["machine", "curated"] = "machine"
    evidence_count: int
    coverage: float = Field(ge=0.0, le=1.0)
    consistency: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)


class VariableFeature(BaseModel):
    key: str
    value_range: list[str]


class WeakFeature(BaseModel):
    key: str
    evidence_count: int


class AllowedImperfection(BaseModel):
    """Imperfection that is acceptable per Authenticity principle — 'trustworthy over beautiful'."""
    value: str
    source: Literal["curated", "observed"] = "observed"

    @model_validator(mode="before")
    @classmethod
    def _coerce_string(cls, data: Any) -> Any:
        if isinstance(data, str):
            return {"value": data, "source": "observed"}
        return data


class ForbiddenRule(BaseModel):
    """A forbidden element — source indicates whether it is curator-declared or AI-observed."""
    rule: str
    source: Literal["curated", "observed"] = "observed"

    @model_validator(mode="before")
    @classmethod
    def _coerce_string(cls, data: Any) -> Any:
        if isinstance(data, str):
            return {"rule": data, "source": "observed"}
        return data


class EvidenceSummary(BaseModel):
    total_images: int
    weak_features: list[WeakFeature] = Field(default_factory=list)


class BaseDNA(BaseModel):
    contract_version: str = CONTRACT_VERSION
    mode: Literal["B"] = "B"
    project: str = ""
    subject: str
    dna_version: str
    schema_id: str = "universal"
    schema_version: str
    prompt_version: str
    provider: str = ""
    model: str = ""
    generated_at: str
    source_images: list[str]
    invariant: list[InvariantFeature]
    variable: list[VariableFeature]
    allowed_imperfections: list[AllowedImperfection] = Field(default_factory=list)
    forbidden: list[ForbiddenRule]
    evidence: EvidenceSummary
    future_capture_notes: list[str] = Field(default_factory=list)
    curator_notes: list[str] = Field(default_factory=list)


# --- Legacy aliases (kept for backward compatibility with old observation cache) ---
DNAFeature = InvariantFeature
