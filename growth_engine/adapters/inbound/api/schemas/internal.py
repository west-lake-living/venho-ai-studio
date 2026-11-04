from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr, model_validator


class AuthorizeMediaReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    http_status: StrictInt = Field(ge=100, le=599)
    content_type: StrictStr = Field(min_length=1, max_length=128)


class AuthorizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["growth.authorize.v2"]
    command_token: StrictStr = Field(min_length=1, max_length=8_192)
    payload_hash: StrictStr = Field(pattern=r"^[0-9a-f]{64}$")
    media_report: AuthorizeMediaReport


AuthorizeReason = Literal[
    "ALREADY_AUTHORIZED",
    "PAUSED",
    "MEDIA_FETCH_FAILED",
    "EPOCH_MISMATCH",
    "WINDOW_CLOSED",
    "PREFLIGHT_BLOCKED",
]


class AuthorizeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["growth.authorize.v2"] = "growth.authorize.v2"
    execute: StrictBool
    reason: AuthorizeReason | None
    execution_id: StrictStr | None
    grant_id: StrictStr | None
    grant_expires_at_ms: StrictInt | None
    remote_page_id: StrictStr | None
    caption: StrictStr | None

    @model_validator(mode="after")
    def validate_decision_shape(self) -> AuthorizeResponse:
        if self.execute:
            if self.reason is not None or any(
                value is None
                for value in (
                    self.execution_id,
                    self.grant_id,
                    self.grant_expires_at_ms,
                    self.remote_page_id,
                    self.caption,
                )
            ):
                raise ValueError("execute=true requires a complete publish grant")
        elif self.reason is None or any(
            value is not None
            for value in (
                self.execution_id,
                self.grant_id,
                self.grant_expires_at_ms,
                self.remote_page_id,
                self.caption,
            )
        ):
            raise ValueError("execute=false requires a reason and no publish grant")
        return self
