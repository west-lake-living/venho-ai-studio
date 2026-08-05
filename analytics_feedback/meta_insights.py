# STATUS (2026-08-06): wired into growth_orchestrator.bridges.m08_analytics
# _bridge.M08AnalyticsBridge as the default metrics_adapter_factory -- the
# real `measure`/`observe()` entry point now goes through this function
# instead of hardcoding MockMetricsAdapter, so `meta_insights_enabled` /
# `real_meta_insights_enabled` actually has an effect. Still returns Mock
# while the flag is off (today's honest state -- no real Facebook/Instagram
# Insights or Zalo OA analytics API integration is implemented below);
# flipping the flag on without first building a real Graph API call in
# this function will raise loudly, which is the correct behavior.
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
