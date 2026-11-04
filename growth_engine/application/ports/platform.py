from __future__ import annotations

from typing import Protocol, runtime_checkable

from growth_engine.application.dto import ChannelConfigView, MetricSpec, PostEvidence, RawMetric


@runtime_checkable
class PlatformReader(Protocol):
    def read_post(self, channel: ChannelConfigView, post_id: str) -> PostEvidence: ...
    def search_recent(
        self, channel: ChannelConfigView, since_ms: int, until_ms: int
    ) -> list[PostEvidence]: ...


@runtime_checkable
class MetricsSource(Protocol):
    def fetch(
        self, channel: ChannelConfigView, post_id: str, metrics: list[MetricSpec]
    ) -> list[RawMetric]: ...
