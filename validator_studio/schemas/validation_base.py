from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class Status(str, Enum):
    OK = "ok"
    WARNING = "warning"
    FAIL = "fail"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MatchState(str, Enum):
    MATCH = "match"
    PARTIAL = "partial"
    MISMATCH = "mismatch"
    NOT_VISIBLE = "not_visible"


class Recommendation(str, Enum):
    APPROVE = "approve"
    REVISE = "revise"
    REGENERATE = "regenerate"
    REJECT = "reject"


class ArtifactRef(BaseModel):
    type: Literal["image", "prompt", "content", "face"]
    file: str
    hash: Optional[str] = None


class SourceKnowledgeRef(BaseModel):
    file: str
    dna_version: Optional[str] = None
    dna_contract_version: Optional[str] = None
    hash: Optional[str] = None


class PromptRef(BaseModel):
    file: str
    prompt_version: Optional[str] = None


class ObserverInfo(BaseModel):
    provider: str = "mock"
    model: str = "mock"
    samples: int = 1


class KillSwitch(BaseModel):
    triggered: bool = False
    reason: str = ""


class DnaSectionScore(BaseModel):
    section: str
    key: Optional[str] = None
    match_state: Optional[MatchState] = None
    score: float
    status: Status
    reason: str = ""
    evidence: str = ""
    category: str = "dna_match"


class ForbiddenViolation(BaseModel):
    rule: str
    source: str = "curated"
    severity: Severity = Severity.HIGH
    violated: bool
    confidence: float = 1.0
    reason: str = ""


class AllowedImperfectionCheck(BaseModel):
    item: str
    present: bool = False
    penalized: bool = False
    reason: str = ""


class Issue(BaseModel):
    issue: str
    severity: Severity
    suggestion: str


class ValidationReport(BaseModel):
    contract_version: str = "1.0"
    module: str = "validator_studio"
    project: str
    subject: str
    validation_type: Literal["image", "prompt", "face", "content"]
    artifact_ref: ArtifactRef
    source_knowledge: list[SourceKnowledgeRef] = Field(default_factory=list)
    prompt_ref: Optional[PromptRef] = None
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    observer: ObserverInfo = Field(default_factory=ObserverInfo)
    kill_switch: KillSwitch = Field(default_factory=KillSwitch)
    overall_score: float = 0
    verdict: Recommendation = Recommendation.REJECT
    dna_match_score: float = 0
    section_scores: list[DnaSectionScore] = Field(default_factory=list)
    category_scores: dict[str, float] = Field(default_factory=dict)
    forbidden_violations: list[ForbiddenViolation] = Field(default_factory=list)
    allowed_imperfections_check: list[AllowedImperfectionCheck] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)
    recommendation: Recommendation = Recommendation.REJECT
    validation_notes: list[str] = Field(default_factory=list)
    raw_observation: dict[str, Any] = Field(default_factory=dict)
