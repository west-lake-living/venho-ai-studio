from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from growth_engine.adapters.inbound.api.auth import Principal, require_scopes
from growth_engine.adapters.inbound.api.schemas.internal import AuthorizeRequest, AuthorizeResponse
from growth_engine.application.publishing.authorize_publish import AuthorizePublishCommand
from growth_engine.domain.kernel.errors import DomainError, ErrorCode


router = APIRouter(tags=["internal-executions"])
_MAX_REQUEST_BYTES = 64 * 1024


@router.post(
    "/internal/growth/v2/executions/authorize",
    status_code=200,
    response_model=AuthorizeResponse,
)
async def authorize_execution(
    body: AuthorizeRequest,
    request: Request,
    response: Response,
    principal: Principal = Depends(require_scopes("execution")),
) -> AuthorizeResponse:
    if len(await request.body()) > _MAX_REQUEST_BYTES:
        raise DomainError(ErrorCode.PAYLOAD_TOO_LARGE, "Request vượt quá giới hạn 64 KB.")
    if not principal.channel_id:
        raise DomainError(ErrorCode.FORBIDDEN, "Bạn không có quyền thực hiện thao tác này.")
    use_case = getattr(request.app.state.container, "authorize_publish", None)
    if use_case is None:
        raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, "Cổng authorize chưa được cấu hình.")

    result = use_case.execute(
        AuthorizePublishCommand(
            command_token=body.command_token,
            payload_hash=body.payload_hash,
            media_report_http_status=body.media_report.http_status,
            media_report_content_type=body.media_report.content_type,
            principal_id=principal.id,
            principal_channel_key=principal.channel_id,
            correlation_id=getattr(request.state, "correlation_id", "authorize"),
        )
    )
    response.headers["Cache-Control"] = "no-store"
    return AuthorizeResponse(
        execute=result.execute,
        reason=result.reason,
        execution_id=result.execution_id,
        grant_id=result.grant_id,
        grant_expires_at_ms=result.grant_expires_at_ms,
        remote_page_id=result.remote_page_id,
        caption=result.caption,
    )
