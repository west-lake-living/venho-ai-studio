from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from growth_engine.application.dto import MetricSpec
from shared.meta.metric_capabilities import capability_state


_USABLE_AVAILABILITY = {"VERIFIED", "AVAILABLE", "READABLE", "CONDITIONAL"}


def load_registry(registry_path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError("metrics registry must be a mapping")
    return payload


def load_metric_specs(registry_path: Path, channel_key: str) -> tuple[MetricSpec, ...]:
    """Load configured metrics with opt-in capabilities defaulting to BLOCKED."""
    payload = load_registry(registry_path)
    metrics = payload.get("metrics", [])
    if not isinstance(metrics, list):
        raise ValueError("metrics registry metrics must be a list")

    result: list[MetricSpec] = []
    for row in metrics:
        if not isinstance(row, dict):
            continue
        channel_keys = row.get("channels")
        if isinstance(channel_keys, list) and channel_key not in channel_keys:
            continue
        availability = str(row.get("availability") or "").upper()
        capability = row.get("capability")
        if availability not in _USABLE_AVAILABILITY:
            continue
        capability_name = str(capability).strip() if capability is not None else None
        scope = str(row.get("scope") or "post")
        state = (
            capability_state(payload, capability_name, channel_key)
            if capability_name
            else ("BLOCKED" if scope == "post_field" else "SUPPORTED")
        )
        period = row.get("period")
        if period is not None and not isinstance(period, str):
            continue
        result.append(
            MetricSpec(
                name=str(row.get("name") or ""),
                provider_field=str(row.get("provider_field") or ""),
                scope=scope,
                period=period,
                capability=capability_name,
                capability_state=state,
                missing_value_state=(
                    str(row["missing_value_state"]).upper()
                    if row.get("missing_value_state") is not None
                    else None
                ),
            )
        )
    return tuple(result)


def load_facebook_engagement_capabilities(registry_path: Path) -> dict[str, str]:
    payload = load_registry(registry_path)
    return {
        "fb_hanoi": capability_state(payload, "facebook_engagement", "fb_hanoi"),
        "fb_venho": capability_state(payload, "facebook_engagement", "fb_venho"),
        "default": "BLOCKED",
    }
