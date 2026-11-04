from __future__ import annotations

from fastapi import APIRouter, Depends, File, Header, Request, Response, UploadFile

from growth_engine.adapters.inbound.api.auth import Principal, require_scopes
from growth_engine.adapters.inbound.api.routers._dashboard import invoke, require_idempotency
from growth_engine.domain.kernel.errors import DomainError, ErrorCode

router = APIRouter(prefix="/api/growth/v2", tags=["growth-dashboard"])
_MAX_ASSET_BYTES = 25 * 1024 * 1024


@router.post("/assets", status_code=202)
def upload_asset(request: Request, response: Response, file: UploadFile = File(...), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"), principal: Principal = Depends(require_scopes("dashboard:write"))) -> object:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise DomainError(ErrorCode.MEDIA_REJECTED, "Chỉ chấp nhận tệp ảnh.")
    return invoke(
        request,
        response,
        "asset.upload",
        payload={"filename": file.filename or "upload", "content_type": file.content_type, "stream": file.file, "max_bytes": _MAX_ASSET_BYTES},
        idempotency_key=require_idempotency(idempotency_key),
    )
