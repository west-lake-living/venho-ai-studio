from __future__ import annotations

from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field

from publishing_gateway.schemas.platform_result import PlatformResult


OverallStatus = Literal["SUCCESS", "PARTIAL_SUCCESS", "FAILED", "DRY_RUN"]


class CircuitBreakerInfo(BaseModel):
    triggered: bool = False
    platform: Optional[str] = None
    state: str = "CLOSED"


class AnalyticsHandoff(BaseModel):
    ready_for_m08: bool = True
    tracking_started_at: str


class DeliveryReceipt(BaseModel):
    contract_version: str = "1.0"
    package_id: str
    project: str
    overall_status: OverallStatus
    published_timestamp: str
    idempotency_key: str
    platform_results: Dict[str, PlatformResult] = Field(default_factory=dict)
    circuit_breaker: CircuitBreakerInfo = Field(default_factory=CircuitBreakerInfo)
    analytics_handoff: AnalyticsHandoff
