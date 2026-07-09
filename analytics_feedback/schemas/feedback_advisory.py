from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class FeedbackRecommendation(BaseModel):
    target: str
    theme: Optional[str] = None
    action: str
    modifier: float
    reason: str
    evidence: Dict[str, Any]


class GuardrailAlerts(BaseModel):
    negative_sentiment_spike: bool = False
    critical_keywords_triggered: List[str] = Field(default_factory=list)


class FeedbackAdvisory(BaseModel):
    contract_version: str = "1.0"
    advisory_id: str
    target_modules: List[str] = Field(default_factory=lambda: ["M01_KNOWLEDGE_STUDIO", "M05_CONTENT_STUDIO"])
    approval_route: List[str] = Field(default_factory=lambda: ["M04_AUTOMATION_STUDIO", "M09_AGENT_STUDIO"])
    generated_timestamp_utc: str
    advisory_type: str = "CONTENT_STRATEGY_ADVISORY"
    status: Literal["pending_approval", "approved", "rejected"] = "pending_approval"
    analysis_summary: str
    recommendations: List[FeedbackRecommendation] = Field(default_factory=list)
    guardrail_alerts: GuardrailAlerts = Field(default_factory=GuardrailAlerts)
    approval_required: bool = True
