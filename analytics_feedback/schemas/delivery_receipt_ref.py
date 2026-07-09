from __future__ import annotations

from typing import Dict, Optional

from pydantic import BaseModel, Field


class PlatformReceiptRef(BaseModel):
    success: bool
    status: str
    post_id: Optional[str] = None
    public_url: Optional[str] = None


class DeliveryReceiptRef(BaseModel):
    contract_version: str = "1.0"
    package_id: str
    project: str
    published_timestamp: str
    content_type: str = "unknown"
    pillar: str = "unknown"
    theme: Optional[str] = None
    platform_results: Dict[str, PlatformReceiptRef] = Field(default_factory=dict)
