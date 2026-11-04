from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from growth_engine.adapters.inbound.api.auth import Principal, require_scopes
from growth_engine.adapters.inbound.api.routers._dashboard import invoke, require_idempotency

router = APIRouter(prefix="/api/growth/v2", tags=["growth-dashboard"])


class BatchApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[dict[str, object]] = Field(min_length=1, max_length=50)


@router.post("/approvals/batch")
def approve_batch(body: BatchApprovalRequest, request: Request, response: Response, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"), principal: Principal = Depends(require_scopes("dashboard:write"))) -> object:
    return invoke(request, response, "approval.batch", payload=body.model_dump(), idempotency_key=require_idempotency(idempotency_key))
