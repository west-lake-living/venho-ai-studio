from __future__ import annotations

from pathlib import Path

import yaml

from analytics_feedback.adapters.mock_metrics import MockMetricsAdapter


def meta_insights_enabled(flags_path: Path = Path("config/projects/venho_hotel/growth/feature_flags.yaml")) -> bool:
    payload = yaml.safe_load(flags_path.read_text(encoding="utf-8")) or {}
    return bool(payload.get("meta_insights_enabled") or payload.get("real_meta_insights_enabled"))


def build_metrics_adapter(platform: str, *, flags_path: Path = Path("config/projects/venho_hotel/growth/feature_flags.yaml")):
    if not meta_insights_enabled(flags_path):
        return MockMetricsAdapter(platform)
    raise RuntimeError("Real Meta Insights provider is feature-flagged for optimization handoff")
