from __future__ import annotations

from fastapi import APIRouter, Depends, File, Header, Request, Response, UploadFile

from growth_engine.adapters.inbound.api.auth import Principal, require_scopes
from growth_engine.adapters.inbound.api.routers._dashboard import invoke, require_idempotency
from growth_engine.domain.kernel.errors import DomainError, ErrorCode

router = APIRouter(prefix="/api/growth/v2", tags=["growth-dashboard"])
_MAX_ASSET_BYTES = 25 * 1024 * 1024


@router.get("/assets/preview/{sha256}", include_in_schema=False)
def preview_asset(
    sha256: str,
    request: Request,
    principal: Principal = Depends(require_scopes("dashboard:read")),
) -> Response:
    service = getattr(request.app.state.container, "dashboard_api", None)
    if service is None or not callable(getattr(service, "preview_image", None)):
        raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, "Xem trước ảnh chưa sẵn sàng.")
    try:
        result = service.preview_image(sha256)
    except Exception as error:
        import sqlite3

        if isinstance(error, sqlite3.Error) or getattr(error, "code", "") == "ERR_GC2_DB_BUSY":
            raise DomainError(ErrorCode.DB_BUSY, "Không đọc được ảnh xem trước.") from error
        raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, "Ảnh xem trước chưa sẵn sàng.") from error
    if result is None:
        raise DomainError(ErrorCode.NOT_FOUND, "Không tìm thấy ảnh xem trước.")
    content, media_type = result
    return Response(
        content=content,
        media_type=media_type,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


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
