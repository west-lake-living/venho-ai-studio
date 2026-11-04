from __future__ import annotations

# _synthetic: true — cần thay bằng fixture thật từ P0-T03/P0-T04.

from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from growth_engine.adapters.outbound.persistence.sqlite.connection import connect
from growth_engine.adapters.outbound.persistence.sqlite.migrator import MigrationRunner
from growth_engine.adapters.outbound.persistence.sqlite.uow import SqliteUnitOfWork
from growth_engine.application.queries.analytics_views import AnalyticsViews


def _ms(day: date, hour: int = 10) -> int:
    return int(datetime.combine(day, time(hour), ZoneInfo("Asia/Ho_Chi_Minh")).timestamp() * 1000)


def test_weekly_view_keeps_page_reach_separate_and_filters_mock_and_dates(tmp_path: Path) -> None:
    database = tmp_path / "analytics.db"
    migrations = Path("growth_engine/adapters/outbound/persistence/sqlite/migrations")
    with connect(database) as connection:
        MigrationRunner(migrations).apply(connection, application_version="synthetic-test")
        for channel_id, key, name, account in (
            ("channel-hanoi", "fb_hanoi", "Ven Hồ Hotel Hanoi", "page-hanoi-synthetic"),
            ("channel-venho", "fb_venho", "Ven Hồ Hotel", "page-venho-synthetic"),
        ):
            connection.execute(
                """INSERT INTO channels
                   (id, project_id, environment, channel_key, platform, remote_account_id, name, created_at)
                   VALUES (?, 'venho_hotel', 'production', ?, 'facebook', ?, ?, 1)""",
                (channel_id, key, account, name),
            )
        for slot_id, channel_id, target_id, delivery_id, package_id, pillar, day, page_id, reach in (
            ("slot-a", "channel-hanoi", "target-a", "delivery-a", "package-a", "local_discovery", date(2026, 11, 2), "channel-hanoi", 100),
            ("slot-b", "channel-venho", "target-b", "delivery-b", "package-b", "food", date(2026, 11, 3), "channel-venho", 200),
        ):
            connection.execute(
                """INSERT INTO slots
                   (id, project_id, local_date, local_time, timezone, lane, cadence_version,
                    scheduled_at, deadline_at, created_at)
                   VALUES (?, 'venho_hotel', ?, '09:00', 'Asia/Ho_Chi_Minh', 'weekly',
                           'synthetic-v1', 1, 2, 1)""",
                (slot_id, day.isoformat()),
            )
            connection.execute(
                "INSERT INTO slot_targets (id, slot_id, channel_id) VALUES (?, ?, ?)",
                (target_id, slot_id, channel_id),
            )
            connection.execute(
                """INSERT INTO content_packages
                   (id, slot_id, topic_key, pillar, lane, source_snapshot_json,
                    fact_snapshot_json, fact_snapshot_hash, generation_version, created_at)
                   VALUES (?, ?, ?, ?, 'weekly', '{\"_synthetic\":true}', '{}', ?, 'test', 1)""",
                (package_id, slot_id, f"topic-{delivery_id}", pillar, "a" * 64),
            )
            connection.execute(
                """INSERT INTO deliveries
                   (id, target_id, channel_id, package_id, state, platform_post_id,
                    published_at, created_at, updated_at)
                   VALUES (?, ?, ?, ?, 'PUBLISHED', ?, ?, 1, 1)""",
                (delivery_id, target_id, channel_id, package_id, f"post-{delivery_id}", _ms(day)),
            )
            connection.execute(
                """INSERT INTO metric_observations
                   (id, delivery_id, metric, checkpoint, observed_at, post_age_seconds,
                    value, value_state, source, api_version)
                   VALUES (?, ?, 'reach', '7d', ?, 604800, ?, 'VALUE', 'meta_graph', 'vXX.X')""",
                (f"metric-{delivery_id}", delivery_id, _ms(day) + 604_800_000, reach),
            )
            connection.execute(
                """INSERT INTO metric_observations
                   (id, delivery_id, metric, checkpoint, observed_at, post_age_seconds,
                    value, value_state, source, api_version)
                   VALUES (?, ?, 'reach', '7d', ?, 604800, 999, 'VALUE', 'mock', 'vXX.X')""",
                (f"mock-{delivery_id}", delivery_id, _ms(day) + 604_800_001),
            )

    views = AnalyticsViews(lambda: SqliteUnitOfWork(lambda: connect(database)))
    report = views.weekly(week_start="2026-11-02", checkpoint="7d")
    next_week = views.weekly(week_start="2026-11-09", checkpoint="7d")

    groups = {row["channel_id"]: row for row in report["groups"]}
    assert groups["channel-hanoi"]["content_effectiveness"]["reach"]["average"] == 100
    assert groups["channel-venho"]["content_effectiveness"]["reach"]["average"] == 200
    assert groups["channel-hanoi"]["pillar"] == "local_discovery"
    assert groups["channel-venho"]["pillar"] == "food"
    assert next_week["groups"] == []
