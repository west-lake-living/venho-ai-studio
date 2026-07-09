from __future__ import annotations

from pydantic import BaseModel, Field


class Task(BaseModel):
    task_id: str
    module: str
    action: str
    input_refs: list[str] = Field(default_factory=list)
    risk_level: str = "read_only"
    approval_required: bool = False
    status: str = "planned"


class TaskPlan(BaseModel):
    contract_version: str = "1.0"
    plan_id: str
    project: str
    agent: str
    goal: str
    tasks: list[Task]
    max_steps: int = 5
    stop_conditions: list[str] = Field(default_factory=lambda: ["missing_required_knowledge", "validator_fail", "approval_required"])
    execution_mode: str = "plan_only"
    approval_required: bool = False
