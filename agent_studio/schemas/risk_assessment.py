from __future__ import annotations

from pydantic import BaseModel, Field


RISK_ORDER = ["read_only", "draft_creation", "internal_file_write", "knowledge_update", "external_impact", "destructive_action"]


class RiskAssessment(BaseModel):
    highest_risk: str = "read_only"
    manual_gate_required: bool = False
    blocked: bool = False
    approvals_required: list[str] = Field(default_factory=list)
