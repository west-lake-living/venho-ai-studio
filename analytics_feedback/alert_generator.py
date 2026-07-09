from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional

from analytics_feedback.schemas.alert_event import AlertEvent, AlertHandoff
from analytics_feedback.schemas.raw_metrics import RawMetrics
from analytics_feedback.sentiment_scorer import SentimentResult


def generate_alert(raw: RawMetrics, sentiment: SentimentResult, project: str, guardrails: Dict[str, object] | None = None) -> Optional[AlertEvent]:
    if not sentiment.negative_sentiment_spike:
        return None
    target = (guardrails or {}).get("alert_target", "M04_AUTOMATION_STUDIO")
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    alert_id = f"alert_{raw.package_id}_{raw.platform}_{raw.snapshot_timestamp_utc.replace(':', '').replace('-', '')}"
    return AlertEvent(
        alert_id=alert_id,
        project=project,
        package_id=raw.package_id,
        severity="CRITICAL",
        alert_type="NEGATIVE_SENTIMENT_SPIKE",
        triggered_at=now,
        platform=raw.platform,
        reason="Negative comments exceeded threshold.",
        metrics={"negative_comment_ratio": sentiment.negative_comment_ratio, "total_comments": sentiment.total_comments},
        handoff=AlertHandoff(target=str(target)),
    )
