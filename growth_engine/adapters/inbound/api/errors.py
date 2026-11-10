from __future__ import annotations

from typing import Mapping

from fastapi import Request
from fastapi.responses import JSONResponse, PlainTextResponse

from growth_engine.adapters.inbound.api.schemas.common import ApiErrorEnvelope
from growth_engine.application.errors import ApplicationError
from growth_engine.domain.kernel.errors import DomainError


_HTTP_STATUS = {
    "ERR_GC2_UNAUTHENTICATED": 401,
    "ERR_GC2_FORBIDDEN": 403,
    "ERR_GC2_CAPABILITY_INVALID": 403,
    "ERR_GC2_NOT_FOUND": 404,
    "ERR_GC2_STATE_CONFLICT": 409,
    "ERR_GC2_ALREADY_AUTHORIZED": 409,
    "ERR_GC2_IDEMPOTENCY_MISMATCH": 409,
    "ERR_GC2_TARGET_TAKEN": 409,
    "ERR_GC2_RECEIPT_CONFLICT": 409,
    "ERR_GC2_REVISION_CONFLICT": 412,
    "ERR_GC2_VALIDATION": 422,
    "ERR_GC2_QC_FAILED": 422,
    "ERR_GC2_MEDIA_NOT_READY": 422,
    "ERR_GC2_MEDIA_REJECTED": 422,
    "ERR_GC2_FACT_EXPIRED": 422,
    "ERR_GC2_DEADLINE_PASSED": 422,
    "ERR_GC2_BUDGET_EXCEEDED": 422,
    "ERR_GC2_PAYLOAD_TOO_LARGE": 413,
    "ERR_GC2_DB_BUSY": 503,
    "ERR_GC2_DEPENDENCY_UNAVAILABLE": 503,
}
_RETRYABLE = frozenset(
    {"ERR_GC2_MEDIA_NOT_READY", "ERR_GC2_DB_BUSY", "ERR_GC2_DEPENDENCY_UNAVAILABLE"}
)
_SAFE_MESSAGES = {
    "ERR_GC2_UNAUTHENTICATED": "Phiên đăng nhập không hợp lệ.",
    "ERR_GC2_FORBIDDEN": "Bạn không có quyền thực hiện thao tác này.",
    "ERR_GC2_CAPABILITY_INVALID": "Lệnh đăng không hợp lệ hoặc đã hết hạn.",
    "ERR_GC2_NOT_FOUND": "Không tìm thấy dữ liệu.",
    "ERR_GC2_STATE_CONFLICT": "Trạng thái bài đã thay đổi; hãy tải lại.",
    "ERR_GC2_ALREADY_AUTHORIZED": "Bài đang được đăng, không thể sửa hoặc thu hồi.",
    "ERR_GC2_IDEMPOTENCY_MISMATCH": "Yêu cầu trùng khoá nhưng khác nội dung.",
    "ERR_GC2_TARGET_TAKEN": "Ô đăng này đã có bài khác.",
    "ERR_GC2_RECEIPT_CONFLICT": "Kết quả đăng mâu thuẫn với bản đã ghi; đã mở sự cố.",
    "ERR_GC2_REVISION_CONFLICT": "Nội dung hoặc ảnh đã thay đổi; hãy mở lại bản xem trước.",
    "ERR_GC2_VALIDATION": "Dữ liệu không hợp lệ.",
    "ERR_GC2_QC_FAILED": "Ảnh hoặc nội dung chưa đạt kiểm tra chất lượng.",
    "ERR_GC2_MEDIA_NOT_READY": "Ảnh đang được xử lý.",
    "ERR_GC2_MEDIA_REJECTED": "Tệp ảnh không hợp lệ hoặc không được hỗ trợ.",
    "ERR_GC2_FACT_EXPIRED": "Thông tin trong bài đã hết hiệu lực.",
    "ERR_GC2_DEADLINE_PASSED": "Đã quá giờ đăng của ô này.",
    "ERR_GC2_BUDGET_EXCEEDED": "Đã chạm hạn mức chi phí AI tháng này.",
    "ERR_GC2_PAYLOAD_TOO_LARGE": "Tệp quá lớn.",
    "ERR_GC2_DB_BUSY": "Hệ thống đang bận, thử lại sau ít giây.",
    "ERR_GC2_DEPENDENCY_UNAVAILABLE": "Dịch vụ phụ thuộc chưa sẵn sàng.",
}


async def domain_error_handler(request: Request, error: DomainError) -> JSONResponse:
    return _error_response(request, error.code, error.message_vi, error.details)


async def application_error_handler(request: Request, error: ApplicationError) -> JSONResponse:
    return _error_response(request, error.code, error.message, error.details)


async def unhandled_error_handler(request: Request, error: Exception) -> PlainTextResponse:
    del error
    headers = {}
    path = request.url.path
    if path == "/media/publish" or path.startswith("/media/publish/"):
        headers["Cache-Control"] = "private, no-store"
    return PlainTextResponse("Internal Server Error", status_code=500, headers=headers)


def _error_response(
    request: Request,
    code: str,
    message: str,
    details: Mapping[str, object],
) -> JSONResponse:
    safe_code = code if code.startswith("ERR_GC2_") else "ERR_GC2_DEPENDENCY_UNAVAILABLE"
    response = ApiErrorEnvelope(
        error={
            "code": safe_code,
            "message": _SAFE_MESSAGES.get(safe_code, message),
            "retryable": safe_code in _RETRYABLE,
            "correlation_id": getattr(request.state, "correlation_id", ""),
            "details": _redact_details(details),
        }
    )
    return JSONResponse(
        status_code=_HTTP_STATUS.get(safe_code, 500),
        content=response.model_dump(),
        headers={"Cache-Control": "no-store"},
    )


def _redact_details(value: Mapping[str, object]) -> dict[str, object]:
    sensitive = ("authorization", "token", "secret", "password", "webhook", "credential")
    result: dict[str, object] = {}
    for key, item in value.items():
        if any(part in key.casefold() for part in sensitive):
            continue
        if isinstance(item, Mapping):
            result[key] = _redact_details(item)
        elif isinstance(item, list):
            result[key] = [
                _redact_details(child) if isinstance(child, Mapping) else child for child in item
            ]
        else:
            result[key] = item
    return result
