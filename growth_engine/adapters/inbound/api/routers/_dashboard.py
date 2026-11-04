from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi import Request, Response

from growth_engine.domain.kernel.errors import DomainError, ErrorCode


SENSITIVE_KEYS = ("authorization", "token", "secret", "password", "webhook", "credential")


def clean(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): clean(item)
            for key, item in value.items()
            if not any(part in str(key).casefold() for part in SENSITIVE_KEYS)
        }
    if isinstance(value, (list, tuple)):
        return [clean(item) for item in value]
    if isinstance(value, str):
        lowered = value.casefold()
        if "make.com" in lowered or "integromat.com" in lowered or "hooks.make" in lowered:
            return "[redacted]"
    return value


def require_idempotency(key: str | None) -> str:
    if key is None or not key.strip() or len(key) > 200:
        raise DomainError(ErrorCode.VALIDATION, "Thiếu Idempotency-Key hợp lệ.")
    return key.strip()


def require_if_match(value: str | None) -> str:
    if value is None or not value.strip():
        raise DomainError(ErrorCode.VALIDATION, "Thiếu If-Match; hãy tải lại dữ liệu trước khi sửa.")
    return value.strip()


def invoke(
    request: Request,
    response: Response,
    operation: str,
    *,
    payload: Mapping[str, object] | None = None,
    if_match: str | None = None,
    idempotency_key: str | None = None,
) -> Any:
    service = getattr(request.app.state.container, "dashboard_api", None)
    if service is None or not callable(getattr(service, "execute", None)):
        raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, "Dashboard API chưa được cấu hình.")
    try:
        result = service.execute(
            operation,
            payload=dict(payload or {}),
            actor=getattr(request.state, "actor", "bff"),
            correlation_id=getattr(request.state, "correlation_id", "dashboard"),
            if_match=if_match,
            idempotency_key=idempotency_key,
        )
    except DomainError:
        raise
    except Exception as error:
        code = getattr(error, "code", "")
        if code == "ERR_GC2_DB_BUSY" or isinstance(error, (OSError, TimeoutError)):
            raise DomainError(ErrorCode.DB_BUSY, "Không đọc/ghi được cơ sở dữ liệu.") from error
        raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, "Dashboard service chưa sẵn sàng.") from error

    body = getattr(result, "body", result)
    etag = getattr(result, "etag", None)
    if etag:
        response.headers["ETag"] = str(etag)
    elif isinstance(body, Mapping):
        delivery_id = body.get("delivery_id")
        row_version = body.get("row_version")
        if isinstance(delivery_id, str) and type(row_version) is int:
            response.headers["ETag"] = f'"delivery:{delivery_id}:{row_version}"'
    response.headers["Cache-Control"] = "no-store"
    return clean(body)
