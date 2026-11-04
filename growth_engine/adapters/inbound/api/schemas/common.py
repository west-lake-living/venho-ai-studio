from __future__ import annotations

from pydantic import BaseModel, Field


class ApiError(BaseModel):
    code: str
    message: str
    retryable: bool
    correlation_id: str
    details: dict[str, object] = Field(default_factory=dict)


class ApiErrorEnvelope(BaseModel):
    error: ApiError


class HealthStatus(BaseModel):
    status: str
    schema_version: int | None = None
