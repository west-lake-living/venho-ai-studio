from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ModuleRequest(BaseModel):
    contract_version: str = "1.0"
    request_id: str
    project: str
    target_module: str
    request_type: str
    source_task_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    approval_required: bool = False
    status: str = "prepared"


class AutomationPackage(BaseModel):
    contract_version: str = "1.0"
    project: str
    plan_id: str
    target_module: str = "M04_AUTOMATION_STUDIO"
    execution_mode: str = "plan_only"
    module_requests: list[ModuleRequest] = Field(default_factory=list)
    approval_required: bool = False
