from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from growth_engine.adapters.inbound.api.auth import Principal, require_scopes
from growth_engine.adapters.inbound.api.routers._dashboard import invoke

router = APIRouter(prefix="/api/growth/v2", tags=["growth-dashboard"])


@router.get("/incidents")
def list_incidents(request: Request, response: Response, state: str = "OPEN", cursor: str | None = None, limit: int = 50, principal: Principal = Depends(require_scopes("dashboard:read"))) -> object:
    if limit < 1 or limit > 50:
        from growth_engine.domain.kernel.errors import DomainError, ErrorCode
        raise DomainError(ErrorCode.VALIDATION, "limit phải nằm trong khoảng 1–50.")
    return invoke(request, response, "incidents.list", payload={"state": state, "cursor": cursor, "limit": limit})
