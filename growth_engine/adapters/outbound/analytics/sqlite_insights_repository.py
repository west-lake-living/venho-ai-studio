from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Sequence

from growth_engine.application.analytics.insights_backfill import MetricObservation, MetricValueState


_SCHEMA = """
CREATE TABLE IF NOT EXISTS metric_observations (
  id               TEXT PRIMARY KEY,
  delivery_id      TEXT NOT NULL REFERENCES deliveries(id),
  metric           TEXT NOT NULL,
  checkpoint       TEXT NOT NULL CHECK(checkpoint IN ('24h','72h','7d','adhoc')),
  observed_at      INTEGER NOT NULL,
  post_age_seconds INTEGER NOT NULL CHECK(post_age_seconds >= 0),
  value            INTEGER,
  value_state      TEXT NOT NULL CHECK(value_state IN ('VALUE','ZERO','NULL','UNAVAILABLE','ERROR')),
  source           TEXT NOT NULL CHECK(source IN ('meta_graph','mock')),
  api_version      TEXT NOT NULL,
  period           TEXT,
  dimensions_json  TEXT NOT NULL DEFAULT '{}',
  error_code       TEXT,
  UNIQUE(delivery_id, metric, checkpoint, observed_at, source),
  CHECK(value_state NOT IN ('VALUE','ZERO') OR value IS NOT NULL),
  CHECK(value_state != 'ZERO' OR value = 0),
  CHECK(value_state IN ('VALUE','ZERO') OR value IS NULL)
);
CREATE TRIGGER IF NOT EXISTS no_metric_update BEFORE UPDATE ON metric_observations
BEGIN SELECT RAISE(ABORT, 'metric_observation_is_append_only'); END;
"""

_INSERT = """
INSERT OR IGNORE INTO metric_observations (
  id, delivery_id, metric, checkpoint, observed_at, post_age_seconds, value,
  value_state, source, api_version, period, dimensions_json, error_code
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


class SQLiteInsightsRepository:
    """Standalone append-only store using the P8 migration 0009 schema."""

    def __init__(self, path: Path) -> None:
        self._connection = sqlite3.connect(str(path))
        self._connection.execute("PRAGMA foreign_keys = OFF")
        self._connection.executescript(_SCHEMA)

    def append(self, observations: Sequence[MetricObservation]) -> int:
        inserted = 0
        with self._connection:
            for observation in observations:
                cursor = self._connection.execute(
                    _INSERT,
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
                inserted += max(cursor.rowcount, 0)
        return inserted

    def load_all(self) -> list[MetricObservation]:
        rows = self._connection.execute(
            "SELECT id, delivery_id, metric, checkpoint, observed_at, post_age_seconds, value, "
            "value_state, source, api_version, period, dimensions_json, error_code "
            "FROM metric_observations ORDER BY observed_at, delivery_id, metric"
        ).fetchall()
        return [
            MetricObservation(
                id=row[0],
                delivery_id=row[1],
                metric=row[2],
                checkpoint=row[3],
                observed_at=row[4],
                post_age_seconds=row[5],
                value=row[6],
                value_state=MetricValueState(row[7]),
                source=row[8],
                api_version=row[9],
                period=row[10],
                dimensions_json=row[11],
                error_code=row[12],
            )
            for row in rows
        ]

    def close(self) -> None:
        self._connection.close()
