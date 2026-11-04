from __future__ import annotations

import threading
import time
from collections.abc import Callable, Mapping
from typing import Any, Protocol

from growth_engine.application.dto import ChannelConfigView, MetricSpec, RawMetric
from growth_engine.adapters.outbound.meta.graph_client import MetaGraphError


class InsightsClient(Protocol):
    def get_insights(self, object_id: str, metrics: list[str], period: str) -> dict[str, Any]: ...


class MetaMetricsSource:
    """Read configured Insights fields one at a time, retaining only the newest sample."""

    source_kind = "meta_graph"

    def __init__(
        self,
        client_factory: Callable[[ChannelConfigView], InsightsClient],
        *,
        now_ms: Callable[[], int] | None = None,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], object] = time.sleep,
        min_interval_seconds: float = 1.0,
    ) -> None:
        if min_interval_seconds < 0:
            raise ValueError("min_interval_seconds must be non-negative")
        self._client_factory = client_factory
        self._now_ms = now_ms or (lambda: time.time_ns() // 1_000_000)
        self._monotonic = monotonic
        self._sleep = sleep
        self._min_interval_seconds = min_interval_seconds
        self._last_request_by_page: dict[str, float] = {}
        self._rate_lock = threading.Lock()

    def fetch(
        self, channel: ChannelConfigView, post_id: str, metrics: list[MetricSpec]
    ) -> list[RawMetric]:
        timestamp = self._now_ms()
        results: list[RawMetric] = []
        client: InsightsClient | None = None
        for spec in metrics:
            unsupported = _unsupported_reason(spec)
            if unsupported is not None:
                results.append(RawMetric(spec.name, None, "UNAVAILABLE", timestamp))
                continue
            object_id = post_id if spec.scope == "post" else channel.remote_account_id
            try:
                if client is None:
                    client = self._client_factory(channel)
                self._wait_for_page_slot(channel.remote_account_id)
                payload = client.get_insights(object_id, [spec.provider_field], spec.period)
            except MetaGraphError as error:
                results.append(
                    RawMetric(spec.name, None, "ERROR", timestamp, _meta_error_code(error))
                )
            except Exception:
                results.append(RawMetric(spec.name, None, "ERROR", timestamp, "SOURCE_ERROR"))
            else:
                results.append(_extract_metric(spec.name, spec.provider_field, payload, timestamp))
        return results

    def _wait_for_page_slot(self, page_id: str) -> None:
        with self._rate_lock:
            now = self._monotonic()
            last = self._last_request_by_page.get(page_id)
            if last is not None:
                wait = self._min_interval_seconds - (now - last)
                if wait > 0:
                    self._sleep(wait)
                    now = self._monotonic()
            self._last_request_by_page[page_id] = now


def _unsupported_reason(spec: MetricSpec) -> str | None:
    values = (spec.name, spec.provider_field, spec.scope, spec.period)
    if any(not isinstance(value, str) or not value.strip() for value in values):
        return "missing configuration"
    if any("REQUIRED_FROM_P0" in value for value in values):
        return "capability evidence is pending"
    if spec.scope not in {"post", "page"}:
        return "scope is not supported by the collector"
    return None


def _extract_metric(name: str, provider_field: str, payload: Mapping[str, Any], timestamp: int) -> RawMetric:
    data = payload.get("data")
    if not isinstance(data, list):
        return RawMetric(name, None, "ERROR", timestamp, "INVALID_RESPONSE")
    item = next(
        (value for value in data if isinstance(value, dict) and value.get("name") == provider_field),
        None,
    )
    if item is None:
        return RawMetric(name, None, "UNAVAILABLE", timestamp)
    values = item.get("values")
    if not isinstance(values, list) or not values:
        return RawMetric(name, None, "UNAVAILABLE", timestamp)
    latest = values[-1]
    if not isinstance(latest, dict) or "value" not in latest:
        return RawMetric(name, None, "ERROR", timestamp, "INVALID_RESPONSE")
    value = latest["value"]
    if value is None:
        return RawMetric(name, None, "NULL", timestamp)
    if type(value) is not int or value < 0:
        return RawMetric(name, None, "ERROR", timestamp, "INVALID_VALUE")
    if value == 0:
        return RawMetric(name, 0, "ZERO", timestamp)
    return RawMetric(name, value, "VALUE", timestamp)


def _meta_error_code(error: MetaGraphError) -> str:
    if error.kind is not None:
        return f"META_{error.kind.value}"
    if error.status is not None:
        return f"META_HTTP_{error.status}"
    return "META_UNCLASSIFIED"
