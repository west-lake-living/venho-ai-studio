from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Callable
from zoneinfo import ZoneInfo

from growth_engine.application.analytics.build_weekly_report import (
    build_weekly_report,
    sample_from_mapping,
)
from growth_engine.application.ports.uow import UnitOfWork
from growth_engine.domain.analytics.metric import MetricCheckpoint


_ICT = ZoneInfo("Asia/Ho_Chi_Minh")
_WEEKLY_CHECKPOINTS = {MetricCheckpoint.H24.value, MetricCheckpoint.H72.value, MetricCheckpoint.D7.value}


class AnalyticsViews:
    """Read published Page-scoped samples for a Monday-starting ICT week."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def weekly(self, *, week_start: str, checkpoint: str) -> dict[str, object]:
        try:
            start = date.fromisoformat(week_start)
        except (TypeError, ValueError) as error:
            raise ValueError("week_start must be an ISO date") from error
        if start.weekday() != 0:
            raise ValueError("week_start must be Monday in Asia/Ho_Chi_Minh")
        if checkpoint not in _WEEKLY_CHECKPOINTS:
            raise ValueError("checkpoint must be one of 24h, 72h, or 7d")
        end = start + timedelta(days=6)
        start_ms = int(datetime.combine(start, time.min, _ICT).timestamp() * 1000)
        until_ms = int(datetime.combine(end + timedelta(days=1), time.min, _ICT).timestamp() * 1000)
        with self._uow_factory().read_only() as tx:
            rows = tx.metrics.load_weekly_samples(
                start_ms=start_ms,
                until_ms=until_ms,
                checkpoint=checkpoint,
            )
        samples = [sample_from_mapping(row) for row in rows]
        return build_weekly_report(
            samples,
            week_start=start.isoformat(),
            week_end=end.isoformat(),
            checkpoint=checkpoint,
        )
