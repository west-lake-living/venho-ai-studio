from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from pydantic import BaseModel, ConfigDict, StrictStr

from growth_engine.adapters.inbound.api.auth import Principal, require_scopes
from growth_engine.adapters.inbound.api.routers._dashboard import invoke, require_idempotency, require_if_match

router = APIRouter(prefix="/api/growth/v2", tags=["growth-dashboard"])


class RescheduleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scheduled_at: StrictStr


@router.get("/slots")
def list_slots(request: Request, response: Response, from_date: str | None = Query(default=None, alias="from"), to_date: str | None = Query(default=None, alias="to"), principal: Principal = Depends(require_scopes("dashboard:read"))) -> object:
    return invoke(request, response, "slots.list", payload={"from": from_date, "to": to_date})


@router.post("/slots/{slot_id}/reschedule")
def reschedule_slot(slot_id: str, body: RescheduleRequest, request: Request, response: Response, if_match: str | None = Header(default=None, alias="If-Match"), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"), principal: Principal = Depends(require_scopes("dashboard:write"))) -> object:
    return invoke(request, response, "slot.reschedule", payload={"slot_id": slot_id, **body.model_dump()}, if_match=require_if_match(if_match), idempotency_key=require_idempotency(idempotency_key))
