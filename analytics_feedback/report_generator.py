from __future__ import annotations

from analytics_feedback.renderers.analytics_report_md import render_analytics_report_md
from analytics_feedback.schemas.feedback_advisory import FeedbackAdvisory
from analytics_feedback.schemas.performance_score import PerformanceScore
from analytics_feedback.schemas.unified_metrics import UnifiedMetrics


def generate_report(snapshot: UnifiedMetrics, score: PerformanceScore, advisory: FeedbackAdvisory) -> str:
    return render_analytics_report_md(snapshot, score, advisory)
