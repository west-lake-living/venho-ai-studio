from __future__ import annotations

from analytics_feedback.schemas.feedback_advisory import FeedbackAdvisory
from analytics_feedback.schemas.performance_score import PerformanceScore
from analytics_feedback.schemas.unified_metrics import UnifiedMetrics


def render_analytics_report_md(snapshot: UnifiedMetrics, score: PerformanceScore, advisory: FeedbackAdvisory) -> str:
    return "\n".join(
        [
            f"# Analytics Report {snapshot.package_id}",
            "",
            "## Snapshot",
            f"- Platform: {snapshot.platform}",
            f"- Content type: {snapshot.content_type}",
            f"- Pillar: {snapshot.pillar}",
            f"- Theme: {snapshot.theme or 'n/a'}",
            "",
            "## Metrics",
            f"- Reach: {snapshot.metrics.reach}",
            f"- Engagement rate by reach: {snapshot.derived.engagement_rate_by_reach}",
            "",
            "## Score",
            f"- Label: {score.performance_label}",
            f"- Relative score: {score.relative_score}",
            f"- Confidence: {score.confidence}",
            "",
            "## Advisory",
            advisory.analysis_summary,
        ]
    ) + "\n"
