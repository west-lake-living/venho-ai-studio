from __future__ import annotations

from typing import Dict, Literal, Union

from pydantic import BaseModel


class AlertHandoff(BaseModel):
    target: str
    requires_human_attention: bool = True


class AlertEvent(BaseModel):
    contract_version: str = "1.0"
    alert_id: str
    project: str
    package_id: str
    severity: Literal["INFO", "WARNING", "CRITICAL"]
    alert_type: str
    triggered_at: str
    platform: str
    reason: str
    metrics: Dict[str, Union[float, int]]
    handoff: AlertHandoff
