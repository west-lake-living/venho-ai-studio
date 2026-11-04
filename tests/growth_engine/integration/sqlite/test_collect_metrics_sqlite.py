from __future__ import annotations

# _synthetic: true — cần thay bằng fixture thật từ P0-T03/P0-T04.

from pathlib import Path

from growth_engine.adapters.outbound.persistence.sqlite.connection import connect
from growth_engine.adapters.outbound.persistence.sqlite.migrator import MigrationRunner
from growth_engine.adapters.outbound.persistence.sqlite.uow import SqliteUnitOfWork
from growth_engine.application.analytics.collect_metrics import CollectMetrics, MetricsCollectionTarget
from growth_engine.application.dto import ChannelConfigView, MetricSpec, RawMetric
from growth_engine.domain.analytics.metric import MetricCheckpoint, ValueState


class Clock:
    def __init__(self, value: int) -> None:
        self.value = value

    def now_ms(self) -> int:
        return self.value


class Ids:
    def __init__(self) -> None:
        self.value = 0

    def new_id(self) -> str:
        self.value += 1
        return f"metric-synthetic-{self.value}"


class MetricsSource:
    source_kind = "mock"

    def __init__(self) -> None:
        self.calls = 0

    def fetch(self, channel, post_id, metrics):
        self.calls += 1
        return [RawMetric("reach", 10, "VALUE", 87)]


def test_collect_metrics_persists_append_only_rows_and_idempotent_sqlite_job(tmp_path: Path) -> None:
    database = tmp_path / "metrics.db"
    migrations = Path("growth_engine/adapters/outbound/persistence/sqlite/migrations")
    with connect(database) as connection:
        MigrationRunner(migrations).apply(connection, application_version="synthetic-test")
        connection.execute(
            """INSERT INTO channels
               (id, project_id, environment, channel_key, platform, remote_account_id, name, created_at)
               VALUES ('channel-synthetic', 'venho_hotel', 'test', 'fb_hanoi', 'facebook',
                       'page-synthetic', 'Synthetic Page', 1)"""
        )
        connection.execute(
            """INSERT INTO slots
               (id, project_id, local_date, local_time, timezone, lane, cadence_version,
                scheduled_at, deadline_at, created_at)
               VALUES ('slot-synthetic', 'venho_hotel', '2026-11-03', '09:00',
                       'Asia/Ho_Chi_Minh', 'weekly', 'cadence-test', 1, 2, 1)"""
        )
        connection.execute(
            """INSERT INTO slot_targets (id, slot_id, channel_id)
               VALUES ('target-synthetic', 'slot-synthetic', 'channel-synthetic')"""
        )
        connection.execute(
            """INSERT INTO content_packages
               (id, slot_id, topic_key, pillar, lane, source_snapshot_json,
                fact_snapshot_json, fact_snapshot_hash, generation_version, created_at)
               VALUES ('package-synthetic', 'slot-synthetic', 'topic-synthetic',
                       'local_discovery', 'weekly', '{\"_synthetic\":true}', '{}', ?,
                       'test-v1', 1)""",
            ("a" * 64,),
        )
        connection.execute(
            """INSERT INTO deliveries
               (id, target_id, channel_id, package_id, state, platform_post_id,
                published_at, created_at, updated_at)
               VALUES ('delivery-synthetic', 'target-synthetic', 'channel-synthetic',
                       'package-synthetic', 'PUBLISHED', 'post-synthetic', 1_000_000, 1, 1)"""
        )

    uow_factory = lambda: SqliteUnitOfWork(lambda: connect(database))
    source = MetricsSource()
    now_ms = 1_000_000 + 24 * 60 * 60 * 1000
    collector = CollectMetrics(uow_factory, source, Ids(), Clock(now_ms))
    target = MetricsCollectionTarget(
        delivery_id="delivery-synthetic",
        channel=ChannelConfigView("fb_hanoi", "page-synthetic", "facebook", "vXX.X"),
        post_id="post-synthetic",
        published_at_ms=1_000_000,
        checkpoint=MetricCheckpoint.H24,
        metrics=(
            MetricSpec("reach", "provider_reach", "post", "day"),
            MetricSpec("comments", "REQUIRED_FROM_P0", "REQUIRED_FROM_P0", "REQUIRED_FROM_P0"),
        ),
    )

    first = collector.execute(target)
    replay = collector.execute(target)

    assert first.observation_count == 2
    assert replay.skipped_duplicate is True
    assert source.calls == 1
    with uow_factory().read_only() as tx:
        rows = tx.connection.execute(
            "SELECT metric, value, value_state, source FROM metric_observations "
            "WHERE delivery_id='delivery-synthetic' ORDER BY metric"
        ).fetchall()
        jobs = tx.connection.execute(
            "SELECT kind, lane, business_key, state FROM jobs WHERE kind='metrics'"
        ).fetchall()
    assert [(row["metric"], row["value"], row["value_state"]) for row in rows] == [
        ("comments", None, "UNAVAILABLE"),
        ("reach", 10, "VALUE"),
    ]
    assert all(row["source"] == "meta_graph" or row["source"] == "mock" for row in rows)
    assert len(jobs) == 1
    assert jobs[0]["lane"] == "jobs"
    assert jobs[0]["state"] == "SUCCEEDED"
    assert "delivery-synthetic" in jobs[0]["business_key"]
