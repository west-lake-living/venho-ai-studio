from __future__ import annotations

# _synthetic: true — cần thay bằng fixture thật từ P0-T03/P0-T04.

import json
from pathlib import Path

from growth_engine.adapters.outbound.persistence.sqlite.connection import connect
from growth_engine.adapters.outbound.persistence.sqlite.migrator import MigrationRunner
from growth_engine.bootstrap import build_container
from growth_engine.settings import Settings
from growth_engine.application.analytics.insights_backfill import (
    BackfillTarget,
    MetricDefinition,
    MetricSample,
    MetricValueState,
    backfill_insights,
)


class _Reader:
    def read_metrics(self, target, definitions):
        return {"reach": MetricSample(MetricValueState.VALUE, 42)}


def test_backfill_repository_uses_migrated_uow_and_replays_idempotently(tmp_path: Path) -> None:
    database = tmp_path / "insights.db"
    connection = connect(database)
    try:
        MigrationRunner(
            Path("growth_engine/adapters/outbound/persistence/sqlite/migrations")
        ).apply(connection, application_version="synthetic-test")
        connection.execute(
            """INSERT INTO channels
               (id, project_id, environment, channel_key, platform, remote_account_id, name, created_at)
               VALUES ('channel-synthetic', 'venho_hotel', 'test', 'ig_venho', 'instagram',
                       'ig-synthetic', 'Synthetic Instagram', 1)"""
        )
        connection.execute(
            """INSERT INTO slots
               (id, project_id, local_date, local_time, timezone, lane, cadence_version,
                scheduled_at, deadline_at, created_at)
               VALUES ('slot-synthetic', 'venho_hotel', '2026-11-04', '09:00',
                       'Asia/Ho_Chi_Minh', 'weekly', 'cadence-test', 1, 2, 1)"""
        )
        connection.execute(
            "INSERT INTO slot_targets (id, slot_id, channel_id) VALUES (?, ?, ?)",
            ("target-synthetic", "slot-synthetic", "channel-synthetic"),
        )
        connection.execute(
            """INSERT INTO content_packages
               (id, slot_id, topic_key, pillar, lane, source_snapshot_json,
                fact_snapshot_json, fact_snapshot_hash, generation_version, created_at)
               VALUES ('package-synthetic', 'slot-synthetic', 'topic-synthetic',
                       'local_discovery', 'weekly', '{"_synthetic":true}', '{}', ?, 'test-v1', 1)""",
            ("a" * 64,),
        )
        connection.execute(
            """INSERT INTO deliveries
               (id, target_id, channel_id, package_id, state, platform_post_id,
                published_at, created_at, updated_at)
               VALUES ('delivery-synthetic', 'target-synthetic', 'channel-synthetic',
                       'package-synthetic', 'PUBLISHED', 'media-synthetic', 1000000, 1, 1)"""
        )
    finally:
        connection.close()
    container = build_container(
        Settings(
            env="test",
            db_path=str(database),
            media_root=str(tmp_path / "media"),
            public_base_url="https://growth.test.invalid",
        )
    )
    uow_factory = container.uow_factory
    repository = container.insights_repository
    target = BackfillTarget(
        channel_id="ig_venho",
        delivery_id="delivery-synthetic",
        post_id="media-synthetic",
        published_at_ms=1_000_000,
        api_version="vTEST",
        pillar="local_discovery",
        image_kind="instagram_photo_v1",
    )
    result = backfill_insights(
        [target], [MetricDefinition("reach", "synthetic_reach", "day")], _Reader(),
        observed_at_ms=2_000_000,
    )

    assert repository.append(result.observations) == 1
    assert repository.append(result.observations) == 0
    stored = repository.load_all()
    assert len(stored) == 1
    assert stored[0].value == 42
    assert json.loads(stored[0].dimensions_json)["channel_id"] == "ig_venho"
    with uow_factory().read_only() as tx:
        row = tx.connection.execute(
            "SELECT source FROM metric_observations WHERE delivery_id='delivery-synthetic'"
        ).fetchone()
    assert row["source"] == "meta_graph"
