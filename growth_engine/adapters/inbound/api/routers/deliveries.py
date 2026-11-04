from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request, Response
from pydantic import BaseModel, ConfigDict, StrictStr

from growth_engine.adapters.inbound.api.auth import Principal, require_scopes
from growth_engine.adapters.inbound.api.routers._dashboard import invoke, require_idempotency, require_if_match

router = APIRouter(prefix="/api/growth/v2", tags=["growth-dashboard"])


class MutationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: StrictStr | None = None
    replace_mode: StrictStr | None = None
    caption: StrictStr | None = None
    variant_id: StrictStr | None = None
    rotation_degrees: int | None = None
    revision_id: StrictStr | None = None
    evidence: dict[str, object] | None = None


@router.get("/deliveries")
def list_deliveries(request: Request, response: Response, state: str | None = None, channel_id: str | None = None, cursor: str | None = None, limit: int = 50, principal: Principal = Depends(require_scopes("dashboard:read"))) -> object:
    if limit < 1 or limit > 50:
        from growth_engine.domain.kernel.errors import DomainError, ErrorCode
        raise DomainError(ErrorCode.VALIDATION, "limit phải nằm trong khoảng 1–50.")
    return invoke(request, response, "deliveries.list", payload={"state": state, "channel_id": channel_id, "cursor": cursor, "limit": limit})


@router.get("/deliveries/{delivery_id}/review")
def review_delivery(delivery_id: str, request: Request, response: Response, principal: Principal = Depends(require_scopes("dashboard:read"))) -> object:
    return invoke(request, response, "delivery.review", payload={"delivery_id": delivery_id})


@router.post("/deliveries/{delivery_id}/revisions")
def create_revision(delivery_id: str, body: MutationRequest, request: Request, response: Response, if_match: str | None = Header(default=None, alias="If-Match"), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"), principal: Principal = Depends(require_scopes("dashboard:write"))) -> object:
    return invoke(request, response, "delivery.revision.create", payload={"delivery_id": delivery_id, **body.model_dump(exclude_none=True)}, if_match=require_if_match(if_match), idempotency_key=require_idempotency(idempotency_key))


def _mutate(operation: str, delivery_id: str, body: MutationRequest, request: Request, response: Response, if_match: str | None, idempotency_key: str | None) -> object:
    return invoke(request, response, operation, payload={"delivery_id": delivery_id, **body.model_dump(exclude_none=True)}, if_match=require_if_match(if_match), idempotency_key=require_idempotency(idempotency_key))


@router.post("/deliveries/{delivery_id}/reject")
def reject_delivery(delivery_id: str, body: MutationRequest, request: Request, response: Response, if_match: str | None = Header(default=None, alias="If-Match"), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"), principal: Principal = Depends(require_scopes("dashboard:write"))) -> object:
    return _mutate("delivery.reject", delivery_id, body, request, response, if_match, idempotency_key)


@router.post("/deliveries/{delivery_id}/revoke")
def revoke_delivery(delivery_id: str, body: MutationRequest, request: Request, response: Response, if_match: str | None = Header(default=None, alias="If-Match"), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"), principal: Principal = Depends(require_scopes("dashboard:write"))) -> object:
    return _mutate("delivery.revoke", delivery_id, body, request, response, if_match, idempotency_key)


@router.post("/deliveries/{delivery_id}/cancel")
def cancel_delivery(delivery_id: str, body: MutationRequest, request: Request, response: Response, if_match: str | None = Header(default=None, alias="If-Match"), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"), principal: Principal = Depends(require_scopes("dashboard:write"))) -> object:
    return _mutate("delivery.cancel", delivery_id, body, request, response, if_match, idempotency_key)


@router.post("/deliveries/{delivery_id}/reconcile")
def reconcile_delivery(delivery_id: str, body: MutationRequest, request: Request, response: Response, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"), principal: Principal = Depends(require_scopes("operator"))) -> object:
    return invoke(request, response, "delivery.reconcile", payload={"delivery_id": delivery_id, **body.model_dump(exclude_none=True)}, idempotency_key=require_idempotency(idempotency_key))


@router.post("/deliveries/{delivery_id}/retry")
def retry_delivery(delivery_id: str, body: MutationRequest, request: Request, response: Response, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"), principal: Principal = Depends(require_scopes("dashboard:write"))) -> object:
    return invoke(request, response, "delivery.retry", payload={"delivery_id": delivery_id, **body.model_dump(exclude_none=True)}, idempotency_key=require_idempotency(idempotency_key))
