from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal


MetricState = Literal["VALUE", "ZERO", "NULL", "UNAVAILABLE"]


@dataclass(frozen=True)
class ObservedMetric:
    name: str
    value: int | float | None
    state: MetricState
    source_value: Any


def normalize_metric(name: str, raw: dict[str, Any]) -> ObservedMetric:
    if name not in raw:
        return ObservedMetric(name=name, value=None, state="UNAVAILABLE", source_value=None)
    source_value = raw[name]
    if source_value is None:
        return ObservedMetric(name=name, value=None, state="NULL", source_value=None)
    if source_value == 0:
        return ObservedMetric(name=name, value=0, state="ZERO", source_value=source_value)
    if isinstance(source_value, (int, float)):
        return ObservedMetric(name=name, value=source_value, state="VALUE", source_value=source_value)
    raise ValueError(f"metric {name} must be numeric, null, or unavailable")


def build_metric_observation(
    *,
    publication_id: str,
    platform: str,
    window: str,
    raw: dict[str, Any],
    metric_names: list[str],
    observed_at: str | None = None,
) -> dict[str, Any]:
    timestamp = observed_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    metrics = {name: normalize_metric(name, raw).__dict__ for name in metric_names}
    return {
        "id": f"metric-{publication_id}-{platform}-{window}",
        "publication_id": publication_id,
        "platform": platform,
        "window": window,
        "observed_at": timestamp,
        "metrics": metrics,
    }


def assert_metrics_match_source(observation: dict[str, Any], raw: dict[str, Any]) -> None:
    for name, metric in observation["metrics"].items():
        if metric["state"] == "UNAVAILABLE":
            if name in raw:
                raise ValueError(f"metric {name} marked unavailable but exists in source")
            continue
        if metric["source_value"] != raw.get(name):
            raise ValueError(f"metric {name} does not match source")
