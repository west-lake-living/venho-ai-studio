from __future__ import annotations

from typing import Any, Dict, List, Optional

from analytics_feedback.adapters.base_metrics_adapter import BaseMetricsAdapter
from analytics_feedback.schemas.raw_metrics import RawMetrics


MOCK_PLATFORM_METRICS: Dict[str, Dict[str, Any]] = {
    "instagram": {
        "impressions": 8900,
        "reach": 7400,
        "likes": 1200,
        "comments": 32,
        "shares": 85,
        "saves": 44,
        "reels_video_view_total_time_ms": 35600000,
    },
    "facebook": {
        "impressions": 4200,
        "reach": 3300,
        "likes": 140,
        "comments": 27,
        "shares": 16,
        "saves": 0,
        "clicks": 18,
    },
    "threads": {"views": 900, "likes": 40, "replies": 6, "shares": 4},
    "google_business": {"views": 1200, "website_clicks": 33, "calls": 5},
}


MOCK_COMMENTS: Dict[str, List[str]] = {
    "instagram": ["Beautiful sunset", "Phong nhin ra ho rat dep", "Love the calm view"],
    "facebook": ["Phong ban qua", "Can refund", "Staff rude", "Khong sach", "dirty room"],
}


class MockMetricsAdapter(BaseMetricsAdapter):
    provider = "mock_insights"

    def __init__(self, platform: str, raw: Optional[Dict[str, Any]] = None, comments: Optional[List[str]] = None) -> None:
        self.platform = platform
        self._raw = raw
        self._comments = comments

    def fetch_metrics(self, package_id: str, post_id: str, snapshot_timestamp_utc: str) -> RawMetrics:
        raw = dict(self._raw if self._raw is not None else MOCK_PLATFORM_METRICS.get(self.platform, {}))
        comments = list(self._comments if self._comments is not None else MOCK_COMMENTS.get(self.platform, []))
        return RawMetrics(
            package_id=package_id,
            platform=self.platform,
            post_id=post_id,
            snapshot_timestamp_utc=snapshot_timestamp_utc,
            provider=self.provider,
            api_version="mock-v1",
            raw=raw,
            comments=comments,
        )
