from __future__ import annotations

from analytics_feedback.schemas.unified_metrics import DerivedMetrics, UnifiedMetrics


def calculate_derived(snapshot: UnifiedMetrics) -> UnifiedMetrics:
    metrics = snapshot.metrics
    reach = metrics.reach or 0
    engagement_count = (metrics.likes or 0) + (metrics.comments or 0) + (metrics.shares or 0) + (metrics.saves or 0)

    def rate(value: int) -> float:
        return round(value / reach, 3) if reach else 0.0

    derived = DerivedMetrics(
        engagement_count=engagement_count,
        engagement_rate_by_reach=rate(engagement_count),
        share_rate=rate(metrics.shares or 0),
        save_rate=rate(metrics.saves or 0),
        click_rate=rate((metrics.clicks or 0) + (metrics.booking_clicks or 0)),
    )
    return snapshot.model_copy(update={"derived": derived})
