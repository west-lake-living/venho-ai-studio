from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class UnifiedMetricValues(BaseModel):
    reach: int = 0
    impressions: int = 0
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    clicks: int = 0
    booking_clicks: int = 0
    watch_time_ms: int = 0


class DerivedMetrics(BaseModel):
    engagement_count: int = 0
    engagement_rate_by_reach: float = 0.0
    share_rate: float = 0.0
    save_rate: float = 0.0
    click_rate: float = 0.0


class MetricProvenance(BaseModel):
    source_adapter: str
    provider: str
    api_version: str


class UnifiedMetrics(BaseModel):
    contract_version: str = "1.0"
    snapshot_id: str
    package_id: str
    project: str
    platform: str
    post_id: str
    snapshot_timestamp_utc: str
    days_since_published: int
    content_type: str
    pillar: str
    theme: Optional[str] = None
    metrics: UnifiedMetricValues
    derived: DerivedMetrics = Field(default_factory=DerivedMetrics)
    provenance: MetricProvenance
