from __future__ import annotations

from datetime import datetime
from typing import Any


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def has_90_day_comparison(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    if not metrics:
        return {"ready": False, "days": 0, "reason": "no_metrics"}
    timestamps = sorted(_parse(item["observed_at"]) for item in metrics)
    days = (timestamps[-1] - timestamps[0]).days + 1
    has_baseline = any(item.get("period") == "baseline" for item in metrics)
    has_candidate = any(item.get("period") == "candidate" for item in metrics)
    ready = days >= 90 and has_baseline and has_candidate
    reason = None if ready else "requires_90_days_baseline_and_candidate"
    return {"ready": ready, "days": days, "reason": reason}
