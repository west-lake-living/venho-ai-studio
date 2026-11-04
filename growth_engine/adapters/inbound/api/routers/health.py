from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from growth_engine.adapters.inbound.api.schemas.common import HealthStatus


router = APIRouter(tags=["health"])


@router.get("/health/live", response_model=HealthStatus)
def live() -> HealthStatus:
    return HealthStatus(status="live")


@router.get("/health/ready", response_model=HealthStatus)
def ready(request: Request) -> HealthStatus | JSONResponse:
    status, schema_version = request.app.state.container.readiness_check()
    if not status:
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return HealthStatus(status="ready", schema_version=schema_version)
