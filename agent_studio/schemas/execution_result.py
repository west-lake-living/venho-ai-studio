from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ExecutionResult(BaseModel):
    contract_version: str = "1.0"
    status: str = "DRY_RUN"
    run_id: str
    project: str
    plan_id: str
    approval_required: bool = False
    module_results: list[dict[str, Any]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
