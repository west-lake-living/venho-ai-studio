from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request, Response
from pydantic import BaseModel, ConfigDict, StrictStr

from growth_engine.adapters.inbound.api.auth import Principal, require_scopes
from growth_engine.adapters.inbound.api.routers._dashboard import invoke, require_idempotency

router = APIRouter(prefix="/api/growth/v2", tags=["growth-dashboard"])


class ControlRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: StrictStr | None = None
    mode: StrictStr | None = None


@router.get("/controls")
def get_controls(request: Request, response: Response, principal: Principal = Depends(require_scopes("dashboard:read"))) -> object:
    return invoke(request, response, "controls.get")


@router.post("/controls/{action}")
def update_control(action: str, body: ControlRequest, request: Request, response: Response, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"), principal: Principal = Depends(require_scopes("operator"))) -> object:
    if action not in {"pause", "resume", "mode"}:
        from growth_engine.domain.kernel.errors import DomainError, ErrorCode
        raise DomainError(ErrorCode.NOT_FOUND, "Không tìm thấy thao tác điều khiển.")
    return invoke(request, response, f"controls.{action}", payload=body.model_dump(exclude_none=True), idempotency_key=require_idempotency(idempotency_key))
