from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from growth_engine.adapters.inbound.api.auth import Principal, require_scopes
from growth_engine.adapters.inbound.api.routers._dashboard import invoke

router = APIRouter(prefix="/api/growth/v2", tags=["growth-dashboard"])


@router.get("/jobs/{job_id}")
def get_job(job_id: str, request: Request, response: Response, principal: Principal = Depends(require_scopes("dashboard:read"))) -> object:
    return invoke(request, response, "job.get", payload={"job_id": job_id})
