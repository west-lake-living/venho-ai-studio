from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


PlatformStatus = Literal["PUBLISHED", "FAILED", "SKIPPED", "DRY_RUN", "QUEUED"]


class PlatformResult(BaseModel):
    platform: str
    success: bool
    status: PlatformStatus
    post_id: Optional[str] = None
    public_url: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
