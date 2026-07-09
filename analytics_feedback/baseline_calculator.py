from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from analytics_feedback.schemas.unified_metrics import UnifiedMetrics


@dataclass(frozen=True)
class Baseline:
    platform: str
    content_type: str
    pillar: str
    sample_size: int
    engagement_rate_by_reach: float
    share_rate: float
    save_rate: float
    click_rate: float


def calculate_baseline(snapshot: UnifiedMetrics, history: Iterable[UnifiedMetrics]) -> Baseline:
    matches: List[UnifiedMetrics] = [
        item
        for item in history
        if item.platform == snapshot.platform and item.content_type == snapshot.content_type and item.pillar == snapshot.pillar
    ]
    if not matches:
        return Baseline(snapshot.platform, snapshot.content_type, snapshot.pillar, 0, 0.0, 0.0, 0.0, 0.0)

    def avg(attr: str) -> float:
        return round(sum(getattr(item.derived, attr) for item in matches) / len(matches), 3)

    return Baseline(
        platform=snapshot.platform,
        content_type=snapshot.content_type,
        pillar=snapshot.pillar,
        sample_size=len(matches),
        engagement_rate_by_reach=avg("engagement_rate_by_reach"),
        share_rate=avg("share_rate"),
        save_rate=avg("save_rate"),
        click_rate=avg("click_rate"),
    )
