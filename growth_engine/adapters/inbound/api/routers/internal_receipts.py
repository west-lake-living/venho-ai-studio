from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, model_validator

from growth_engine.adapters.inbound.api.auth import Principal, require_scopes
from growth_engine.application.publishing.receive_receipt import (
    ReceiptPersistenceUnavailable,
    ReceiveReceiptCommand,
)
from growth_engine.domain.kernel.errors import DomainError, ErrorCode


router = APIRouter(tags=["internal-receipts"])
_MAX_REQUEST_BYTES = 64 * 1024
ReceiptOutcomeValue = Literal["POST_CREATED", "REJECTED_NO_SIDE_EFFECT", "OUTCOME_UNKNOWN"]
FailedStepValue = Literal["FETCH_MEDIA", "AUTHORIZE", "CREATE_POST"]


class ReceiptErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    class_name: StrictStr = Field(alias="class", min_length=1, max_length=128, pattern=r"^[A-Z0-9_.-]+$")
    message: StrictStr = Field(min_length=1, max_length=4_096)


class ReceiptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_version: Literal["growth.receipt.v2"]
    event_id: StrictStr = Field(min_length=1, max_length=256)
    command_id: StrictStr = Field(min_length=1, max_length=128)
    execution_id: StrictStr = Field(min_length=1, max_length=128)
    grant_id: StrictStr = Field(min_length=1, max_length=128)
    delivery_id: StrictStr = Field(min_length=1, max_length=128)
    revision_id: StrictStr = Field(min_length=1, max_length=128)
    channel_id: StrictStr = Field(min_length=1, max_length=128)
    remote_page_id: StrictStr = Field(min_length=1, max_length=256)
    payload_hash: StrictStr = Field(pattern=r"^[0-9a-f]{64}$")
    outcome: ReceiptOutcomeValue
    platform_post_id: StrictStr | None = Field(default=None, max_length=512)
    permalink: StrictStr | None = Field(default=None, max_length=2_048, pattern=r"^https://")
    failed_step: FailedStepValue | None = None
    error: ReceiptErrorBody | None = None
    occurred_at_ms: StrictInt = Field(ge=0)

    @model_validator(mode="after")
    def validate_event_identity(self) -> ReceiptRequest:
        if self.event_id != f"{self.grant_id}:{self.outcome}":
            raise ValueError("event_id must be deterministic for grant and outcome")
        if self.outcome == "REJECTED_NO_SIDE_EFFECT" and self.error is None:
            raise ValueError("rejected receipt requires error details")
        return self


class ReceiptResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["growth.receipt.v2"] = "growth.receipt.v2"
    receipt_id: StrictStr
    accepted: bool = True
    duplicate: bool = False


@router.post(
    "/internal/growth/v2/receipts",
    status_code=200,
    response_model=ReceiptResponse,
)
async def receive_receipt(
    body: ReceiptRequest,
    request: Request,
    response: Response,
    principal: Principal = Depends(require_scopes("receipt")),
) -> ReceiptResponse:
    if len(await request.body()) > _MAX_REQUEST_BYTES:
        raise DomainError(ErrorCode.PAYLOAD_TOO_LARGE, "Request vượt quá giới hạn 64 KB.")
    use_case = getattr(request.app.state.container, "receive_receipt", None)
    if use_case is None:
        raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, "Receipt inbox chưa được cấu hình.")
    try:
        result = use_case.execute(
            ReceiveReceiptCommand(
                issuer_id=principal.id,
                body=body.model_dump(mode="json", by_alias=True),
                correlation_id=getattr(request.state, "correlation_id", "receipt"),
            )
        )
    except ReceiptPersistenceUnavailable as error:
        raise DomainError(ErrorCode.DB_BUSY, "Không ghi được receipt; Make có thể gửi lại callback.") from error
    response.headers["Cache-Control"] = "no-store"
    return ReceiptResponse(
        receipt_id=result.receipt_id,
        accepted=result.accepted,
        duplicate=result.duplicate,
    )
