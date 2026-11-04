from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request, Response
from pydantic import BaseModel, ConfigDict, StrictStr

from growth_engine.adapters.inbound.api.auth import Principal, require_scopes
from growth_engine.adapters.inbound.api.routers._dashboard import invoke, require_idempotency

router = APIRouter(prefix="/api/growth/v2", tags=["growth-dashboard"])


class CandidateDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_hash: StrictStr
    decision: StrictStr
    reason: StrictStr | None = None


@router.get("/candidates")
def list_candidates(request: Request, response: Response, state: str = "NEW", cursor: str | None = None, limit: int = 50, principal: Principal = Depends(require_scopes("dashboard:read"))) -> object:
    if limit < 1 or limit > 50:
        from growth_engine.domain.kernel.errors import DomainError, ErrorCode
        raise DomainError(ErrorCode.VALIDATION, "limit phải nằm trong khoảng 1–50.")
    return invoke(request, response, "candidates.list", payload={"state": state, "cursor": cursor, "limit": limit})


@router.post("/candidates/{candidate_id}/decision")
def decide_candidate(candidate_id: str, body: CandidateDecisionRequest, request: Request, response: Response, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"), principal: Principal = Depends(require_scopes("dashboard:write"))) -> object:
    return invoke(request, response, "candidate.decide", payload={"candidate_id": candidate_id, **body.model_dump()}, idempotency_key=require_idempotency(idempotency_key))
