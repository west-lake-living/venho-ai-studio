from __future__ import annotations

from datetime import datetime, timezone

from analytics_feedback.schemas.feedback_advisory import FeedbackAdvisory, FeedbackRecommendation, GuardrailAlerts
from analytics_feedback.schemas.performance_score import PerformanceScore
from analytics_feedback.schemas.unified_metrics import UnifiedMetrics
from analytics_feedback.sentiment_scorer import SentimentResult


def generate_feedback_advisory(snapshot: UnifiedMetrics, score: PerformanceScore, sentiment: SentimentResult) -> FeedbackAdvisory:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    recommendations = []
    evidence = {
        "package_id": snapshot.package_id,
        "platform": snapshot.platform,
        "pillar": snapshot.pillar,
        "theme": snapshot.theme,
        "relative_score": score.relative_score,
    }
    if score.performance_label == "OUTPERFORM" and not sentiment.negative_sentiment_spike:
        recommendations.append(
            FeedbackRecommendation(
                target=f"content_pillars.{snapshot.pillar}",
                theme=snapshot.theme,
                action="INCREASE_WEIGHT",
                modifier=1.25,
                reason=f"{snapshot.platform} content outperformed the {snapshot.pillar} baseline by {round((score.relative_score - 1) * 100)}%.",
                evidence=evidence,
            )
        )
    elif score.performance_label == "UNDERPERFORM":
        recommendations.append(
            FeedbackRecommendation(
                target=f"content_pillars.{snapshot.pillar}",
                theme=snapshot.theme,
                action="DECREASE_WEIGHT",
                modifier=0.8,
                reason=f"{snapshot.platform} content underperformed the {snapshot.pillar} baseline by {round((1 - score.relative_score) * 100)}%.",
                evidence=evidence,
            )
        )
    summary = f"{snapshot.platform} {snapshot.content_type} performance is {score.performance_label.lower()} for pillar {snapshot.pillar}."
    return FeedbackAdvisory(
        advisory_id=f"adv_{snapshot.package_id}_{snapshot.platform}",
        generated_timestamp_utc=now,
        analysis_summary=summary,
        recommendations=recommendations,
        guardrail_alerts=GuardrailAlerts(
            negative_sentiment_spike=sentiment.negative_sentiment_spike,
            critical_keywords_triggered=sentiment.critical_keywords_triggered,
        ),
    )
