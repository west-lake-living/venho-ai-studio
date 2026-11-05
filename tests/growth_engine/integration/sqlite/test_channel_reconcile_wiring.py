from __future__ import annotations

# _synthetic: true — cần thay bằng fixture thật từ P0-T03/P0-T04.

from pathlib import Path

from growth_engine.adapters.outbound.persistence.sqlite.connection import connect
from growth_engine.adapters.outbound.persistence.sqlite.migrator import MigrationRunner
from growth_engine.bootstrap import build_container
from growth_engine.settings import Settings
from growth_engine.application.ops.channel_reconcile import (
    Channel,
    ChannelPost,
    ChannelReconcileStatus,
    ScheduledSlot,
    reconcile_channels,
)


class _EmptyReader:
    def list_recent_posts(self, account_id, since_ms, until_ms, fields, max_pages):
        return []

    def get_post(self, account_id, post_id, fields):
        raise AssertionError("no known post id is expected in this synthetic fixture")


def test_reconcile_alerts_are_deduped_in_migrated_sqlite_uow(tmp_path: Path) -> None:
    database = tmp_path / "reconcile.db"
    connection = connect(database)
    try:
        MigrationRunner(
            Path("growth_engine/adapters/outbound/persistence/sqlite/migrations")
        ).apply(connection, application_version="synthetic-test")
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
    result = reconcile_channels(
        [ScheduledSlot("slot-synthetic", 1_800_000_000_000, "Approved synthetic caption")],
        [Channel("fb_hanoi", "page-synthetic", ("synthetic_id", "synthetic_caption"))],
        [],
        _EmptyReader(),
    )
    assert result[0].status is ChannelReconcileStatus.MISSING

    store = container.channel_reconcile_store
    assert store.record_new_alerts(result, now_ms=1_800_000_001_000) == tuple(result)
    assert store.record_new_alerts(result, now_ms=1_800_000_002_000) == ()

    with uow_factory().read_only() as tx:
        rows = tx.connection.execute(
            "SELECT type, state, occurrence_count, details_json FROM incidents"
        ).fetchall()
    assert len(rows) == 1
    assert rows[0]["type"] == "CHANNEL_RECONCILE_MISSING"
    assert rows[0]["state"] == "OPEN"
    assert rows[0]["occurrence_count"] == 2
    assert '"slot_id":"slot-synthetic"' in rows[0]["details_json"]
