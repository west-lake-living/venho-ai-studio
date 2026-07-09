from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict

from analytics_feedback.baseline_calculator import Baseline
from analytics_feedback.schemas.performance_score import PerformanceScore
from analytics_feedback.schemas.unified_metrics import UnifiedMetrics


DEFAULT_SCORING_RULES = {
    "minimum_sample_size": 5,
    "strong_conclusion_sample_size": 20,
    "confidence_levels": {"low": 5, "medium": 12, "high": 20},
    "outperform_threshold": 1.25,
    "underperform_threshold": 0.75,
}


def score_snapshot(snapshot: UnifiedMetrics, baseline: Baseline, rules: Dict[str, object] | None = None) -> PerformanceScore:
    rules = {**DEFAULT_SCORING_RULES, **(rules or {})}
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    minimum = int(rules["minimum_sample_size"])
    strong = int(rules["strong_conclusion_sample_size"])
    warnings = []

    if baseline.sample_size < minimum or baseline.engagement_rate_by_reach <= 0:
        label = "INSUFFICIENT_DATA"
        relative = 0.0
        reasons = ["Not enough baseline history for this platform/content/pillar group"]
        confidence = "low"
    else:
        relative = round(snapshot.derived.engagement_rate_by_reach / baseline.engagement_rate_by_reach, 2)
        if relative >= float(rules["outperform_threshold"]):
            label = "OUTPERFORM"
            reasons = [f"Engagement rate is {round((relative - 1) * 100)}% above baseline"]
        elif relative <= float(rules["underperform_threshold"]):
            label = "UNDERPERFORM"
            reasons = [f"Engagement rate is {round((1 - relative) * 100)}% below baseline"]
        else:
            label = "NORMAL"
            reasons = ["Engagement rate is within normal baseline range"]
        confidence = _confidence(baseline.sample_size, rules.get("confidence_levels", {}))
        if baseline.sample_size < strong:
            warnings.append(f"Sample size {baseline.sample_size} < strong_conclusion_sample_size ({strong}), avoid strong conclusion")
            confidence = "low" if baseline.sample_size < 12 else "medium"

    return PerformanceScore(
        snapshot_id=snapshot.snapshot_id,
        package_id=snapshot.package_id,
        platform=snapshot.platform,
        score_timestamp_utc=now,
        baseline_group={"platform": baseline.platform, "content_type": baseline.content_type, "pillar": baseline.pillar},
        sample_size=baseline.sample_size,
        performance_label=label,
        relative_score=relative,
        confidence=confidence,
        reasons=reasons,
        warnings=warnings,
    )


def _confidence(sample_size: int, levels: Dict[str, object]) -> str:
    high = int(levels.get("high", 20))
    medium = int(levels.get("medium", 12))
    if sample_size >= high:
        return "high"
    if sample_size >= medium:
        return "medium"
    return "low"
