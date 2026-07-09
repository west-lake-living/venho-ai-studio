from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class AgentConstraints(BaseModel):
    language: str = "vi"
    validation_level: str = "standard"
    max_steps: int = Field(default=5, ge=1, le=20)
    allow_external_actions: bool = False


class AgentRequest(BaseModel):
    contract_version: str = "1.0"
    project: str
    agent: str
    goal: str
    context: dict[str, Any] = Field(default_factory=dict)
    constraints: AgentConstraints = Field(default_factory=AgentConstraints)
    execution_mode: Literal["plan_only", "dry_run", "execute"] = "plan_only"
    use_mock_engine: bool = True

    @field_validator("project", "agent", "goal")
    @classmethod
    def required_text(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("field is required")
        return value.strip()
