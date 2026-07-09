from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Persona(BaseModel):
    agent_id: str
    display_name: str
    type: str = "generic"
    base_agent: str = "content_planning_agent"
    role: str = ""
    scope: list[str] = Field(default_factory=list)
    required_knowledge: list[str] = Field(default_factory=list)
    allowed_modules: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(default_factory=list)
    validation_level: str = "standard"
    approval_required_for: list[str] = Field(default_factory=list)
    notes: Optional[str] = None

    @field_validator("agent_id", "display_name", "base_agent")
    @classmethod
    def required_text(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("field is required")
        return value.strip()
