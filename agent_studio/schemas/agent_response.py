from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from agent_studio.schemas.risk_assessment import RiskAssessment
from agent_studio.schemas.task_plan import TaskPlan


class AgentResponse(BaseModel):
    contract_version: str = "1.0"
    agent_name: str
    project: str
    status: str
    execution_mode: str
    confidence_score: float = 0.8
    knowledge_sources_used: list[str] = Field(default_factory=list)
    plan: Optional[TaskPlan] = None
    module_requests: list[dict[str, Any]] = Field(default_factory=list)
    validation_summary: dict[str, Any] = Field(default_factory=dict)
    missing_knowledge: list[str] = Field(default_factory=list)
    risk_assessment: RiskAssessment = Field(default_factory=RiskAssessment)
    execution_log: list[str] = Field(default_factory=list)
    error_code: Optional[str] = None
