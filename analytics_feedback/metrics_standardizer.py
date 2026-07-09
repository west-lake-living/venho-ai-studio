from __future__ import annotations

from analytics_feedback.schemas.delivery_receipt_ref import DeliveryReceiptRef
from analytics_feedback.schemas.raw_metrics import RawMetrics
from analytics_feedback.schemas.unified_metrics import MetricProvenance, UnifiedMetrics, UnifiedMetricValues
from analytics_feedback.utils.idempotency import snapshot_id
from analytics_feedback.utils.stats_calculator import calculate_derived
from analytics_feedback.utils.time_windows import days_since


def standardize_metrics(raw: RawMetrics, receipt: DeliveryReceiptRef, source_adapter: str | None = None) -> UnifiedMetrics:
    data = raw.raw
    reach_raw = data.get("reach")
    reach = int(reach_raw if reach_raw is not None else (data.get("views") or data.get("impressions") or 0))
    impressions = int(data.get("impressions") or data.get("views") or reach)
    values = UnifiedMetricValues(
        reach=reach,
        impressions=impressions,
        views=int(data.get("views") or data.get("plays") or impressions),
        likes=int(data.get("likes") or 0),
        comments=int(data.get("comments") or data.get("replies") or 0),
        shares=int(data.get("shares") or 0),
        saves=int(data.get("saves") or 0),
        clicks=int(data.get("clicks") or data.get("website_clicks") or 0),
        booking_clicks=int(data.get("booking_clicks") or 0),
        watch_time_ms=int(data.get("watch_time_ms") or data.get("reels_video_view_total_time_ms") or 0),
    )
    snapshot = UnifiedMetrics(
        snapshot_id=snapshot_id(raw.package_id, raw.platform, raw.snapshot_timestamp_utc),
        package_id=raw.package_id,
        project=receipt.project,
        platform=raw.platform,
        post_id=raw.post_id,
        snapshot_timestamp_utc=raw.snapshot_timestamp_utc,
        days_since_published=days_since(receipt.published_timestamp, raw.snapshot_timestamp_utc),
        content_type=receipt.content_type,
        pillar=receipt.pillar,
        theme=receipt.theme,
        metrics=values,
        provenance=MetricProvenance(
            source_adapter=source_adapter or f"{raw.platform}_insights",
            provider=raw.provider,
            api_version=raw.api_version,
        ),
    )
    return calculate_derived(snapshot)
