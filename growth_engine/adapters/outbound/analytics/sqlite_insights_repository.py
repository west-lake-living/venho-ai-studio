from __future__ import annotations

from typing import Any, Callable, Sequence

from growth_engine.application.analytics.insights_backfill import MetricObservation
from growth_engine.application.analytics.insights_backfill import MetricValueState


class SQLiteInsightsRepository:
    """Append-only insight adapter using the application's migrated SQLite UoW."""

    def __init__(self, uow_factory: Callable[[], Any]) -> None:
        if not callable(uow_factory):
            raise TypeError("uow_factory must be callable")
        self._uow_factory = uow_factory

    def append(self, observations: Sequence[MetricObservation]) -> int:
        inserted = 0
        with self._uow_factory().begin_immediate() as tx:
            for observation in observations:
                cursor = tx.connection.execute(
                    """INSERT OR IGNORE INTO metric_observations
                       (id, delivery_id, metric, checkpoint, observed_at,
                        post_age_seconds, value, value_state, source, api_version,
                        period, dimensions_json, error_code)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        observation.id,
                        observation.delivery_id,
                        observation.metric,
                        observation.checkpoint,
                        observation.observed_at,
                        observation.post_age_seconds,
                        observation.value,
                        observation.value_state.value,
                        observation.source,
                        observation.api_version,
                        observation.period,
                        observation.dimensions_json,
                        observation.error_code,
                    ),
                )
                inserted += cursor.rowcount
        return inserted

    def load_all(self) -> list[MetricObservation]:
        with self._uow_factory().read_only() as tx:
            rows = tx.connection.execute(
                "SELECT id, delivery_id, metric, checkpoint, observed_at, post_age_seconds, value, "
                "value_state, source, api_version, period, dimensions_json, error_code "
                "FROM metric_observations ORDER BY observed_at, delivery_id, metric"
            ).fetchall()
        return [
            MetricObservation(
                id=row["id"],
                delivery_id=row["delivery_id"],
                metric=row["metric"],
                checkpoint=row["checkpoint"],
                observed_at=row["observed_at"],
                post_age_seconds=row["post_age_seconds"],
                value=row["value"],
                value_state=MetricValueState(row["value_state"]),
                source=row["source"],
                api_version=row["api_version"],
                period=row["period"],
                dimensions_json=row["dimensions_json"],
                error_code=row["error_code"],
            )
            for row in rows
        ]
