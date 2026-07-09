from __future__ import annotations

from abc import ABC, abstractmethod

from analytics_feedback.schemas.raw_metrics import RawMetrics


class BaseMetricsAdapter(ABC):
    platform: str
    provider: str

    @abstractmethod
    def fetch_metrics(self, package_id: str, post_id: str, snapshot_timestamp_utc: str) -> RawMetrics:
        raise NotImplementedError
