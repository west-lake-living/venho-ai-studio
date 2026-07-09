from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class RawMetrics(BaseModel):
    contract_version: str = "1.0"
    package_id: str
    platform: str
    post_id: str
    snapshot_timestamp_utc: str
    provider: str
    api_version: str = "mock"
    raw: Dict[str, Any] = Field(default_factory=dict)
    comments: List[str] = Field(default_factory=list)
