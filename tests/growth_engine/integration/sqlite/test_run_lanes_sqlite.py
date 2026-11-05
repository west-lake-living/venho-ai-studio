from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from growth_engine.adapters.outbound.persistence.sqlite.connection import connect
from growth_engine.adapters.outbound.persistence.sqlite.generation_store import SqliteGenerationStore
from growth_engine.adapters.outbound.persistence.sqlite.lane_store import SqliteRunLanesStore
from growth_engine.adapters.outbound.persistence.sqlite.migrator import MigrationRunner
from growth_engine.adapters.outbound.persistence.sqlite.uow import SqliteUnitOfWork
from growth_engine.application.content.run_lanes import LanePackage, RunLanes
from growth_engine.application.scheduling.ensure_slots import EnsureSlots
from growth_engine.application.scheduling.reserve_target import ReserveTarget
from growth_engine.domain.content.package import ContentPackage
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.states import DeliveryState
from growth_engine.domain.kernel.hashing import sha256_hex
from growth_engine.domain.scheduling.cadence import CadencePolicy, CadenceRule


NOW_MS = int(datetime(2026, 11, 2, 1, 0, tzinfo=timezone.utc).timestamp() * 1000)


class _Clock:
    def now_ms(self) -> int:
        return NOW_MS


class _Ids:
    def __init__(self) -> None:
        self.value = 0

    def new_id(self) -> str:
        self.value += 1
        return f"lane-id-{self.value}"


class _PackageFactory:
    def __init__(self, package: LanePackage, uow_factory) -> None:
        self.package = package
        self.uow_factory = uow_factory
        self.calls: list[tuple[str, str, tuple[str, ...]]] = []

    def create(self, slot_id: str, lane: str, *, excluded_topic_keys: tuple[str, ...]) -> LanePackage:
        self.calls.append((slot_id, lane, excluded_topic_keys))
        with self.uow_factory().begin_immediate() as tx:
            if tx.packages.get(self.package.package_id) is None:
                tx.packages.save(_package(slot_id, self.package.package_id))
        return self.package


def _policy() -> CadencePolicy:
    return CadencePolicy(
        version=2,
        project_id="venho_hotel",
        timezone="Asia/Ho_Chi_Minh",
        publish_time="09:00",
        rules=(CadenceRule(0, "regular", "regular"),),
    )


def _setup(tmp_path: Path):
    database = tmp_path / "lanes.sqlite"
    connection = connect(database)
    try:
        MigrationRunner(Path("growth_engine/adapters/outbound/persistence/sqlite/migrations")).apply(
            connection, application_version="run-lanes-integration"
        )
        for key, platform in (("fb_hanoi", "facebook"), ("fb_venho", "facebook"), ("ig_venho", "instagram")):
            connection.execute(
                """INSERT INTO channels
                   (id, project_id, environment, channel_key, platform, remote_account_id,
                    name, enabled, paused, created_at)
                   VALUES (?, 'venho_hotel', 'test', ?, ?, ?, ?, 1, 0, 1)""",
                (f"channel-{key}", key, platform, f"synthetic-{key}", f"Synthetic {key}"),
            )
    finally:
        connection.close()
    uow_factory = lambda: SqliteUnitOfWork(lambda: connect(database), sleep=lambda _: None)
    ids = _Ids()
    store = SqliteGenerationStore(uow_factory, ids)
    ensure = EnsureSlots(store, _Clock(), ids)
    lane_store = SqliteRunLanesStore(
        uow_factory, ensure, _policy(), environment="test", timezone_name="Asia/Ho_Chi_Minh"
    )
    result = lane_store.ensure_slots(NOW_MS, horizon_days=1)
    assert result.targets_created == 3
    return uow_factory, ids, store, lane_store


def _package(
    slot_id: str,
    package_id: str = "package-lane-synthetic",
    *,
    created_at_ms: int = NOW_MS,
) -> ContentPackage:
    return ContentPackage(
        id=package_id,
        slot_id=slot_id,
        topic_key="topic-lane-synthetic",
        pillar="west_lake_life",
        lane="regular",
        source_snapshot_json='{"_synthetic":true,"captions_by_profile":{"default":"Synthetic caption"},"images":[]}',
        fact_snapshot_json="{}",
        fact_snapshot_hash=sha256_hex(b"{}"),
        generation_version="synthetic-v1",
        created_at_ms=created_at_ms,
    )


def test_sqlite_run_lanes_reserves_each_page_from_one_shared_package(tmp_path: Path) -> None:
    uow_factory, ids, store, lane_store = _setup(tmp_path)
    package_factory = _PackageFactory(
        LanePackage("package-lane-synthetic", "topic-lane-synthetic"), uow_factory
    )
    runner = RunLanes(lane_store, package_factory, ReserveTarget(store, _Clock(), ids), _Clock())

    result = runner.run_fast(horizon_days=1)

    assert len(package_factory.calls) == 1
    assert len(result.reserved_target_ids) == 3
    with uow_factory().read_only() as tx:
        deliveries = tx.connection.execute(
            "SELECT target_id, package_id, state FROM deliveries ORDER BY target_id"
        ).fetchall()
        jobs = tx.connection.execute(
            "SELECT kind, payload_json FROM jobs WHERE kind='assemble_revision' ORDER BY id"
        ).fetchall()
    assert len(deliveries) == 3
    assert {row["package_id"] for row in deliveries} == {"package-lane-synthetic"}
    assert {row["state"] for row in deliveries} == {"DRAFT"}
    assert len(jobs) == 3
    assembly = [json.loads(row["payload_json"]) for row in jobs]
    assert {row["media_profile"] for row in assembly if row["platform"] == "instagram"} == {
        "instagram_photo_v1"
    }
    assert {row["media_profile"] for row in assembly if row["platform"] == "facebook"} == {
        "facebook_photo_v1"
    }


def test_sqlite_fast_lane_skips_published_page_and_only_reserves_pending_pages(tmp_path: Path) -> None:
    uow_factory, ids, store, lane_store = _setup(tmp_path)
    with uow_factory().begin_immediate() as tx:
        slot = tx.connection.execute("SELECT id FROM slots").fetchone()
        target = tx.connection.execute(
            "SELECT st.id, st.channel_id FROM slot_targets st JOIN channels c ON c.id=st.channel_id "
            "WHERE c.channel_key='fb_hanoi'"
        ).fetchone()
        tx.packages.save(_package(
            str(slot["id"]), created_at_ms=NOW_MS - 121 * 24 * 60 * 60 * 1000
        ))
        tx.deliveries.save(
            Delivery("delivery-published-synthetic", DeliveryState.PUBLISHED),
            target_id=str(target["id"]),
            channel_id=str(target["channel_id"]),
            package_id="package-lane-synthetic",
            created_at_ms=NOW_MS,
            updated_at_ms=NOW_MS,
            platform_post_id="synthetic-post-id",
        )
    package_factory = _PackageFactory(
        LanePackage("package-lane-synthetic", "topic-lane-synthetic"), uow_factory
    )
    runner = RunLanes(lane_store, package_factory, ReserveTarget(store, _Clock(), ids), _Clock())

    result = runner.run_fast(horizon_days=1)

    assert len(package_factory.calls) == 1
    assert len(result.reserved_target_ids) == 2
    with uow_factory().read_only() as tx:
        rows = tx.connection.execute(
            "SELECT c.channel_key, d.state FROM deliveries d JOIN channels c ON c.id=d.channel_id "
            "ORDER BY c.channel_key"
        ).fetchall()
    assert [(row["channel_key"], row["state"]) for row in rows] == [
        ("fb_hanoi", "PUBLISHED"),
        ("fb_venho", "DRAFT"),
        ("ig_venho", "DRAFT"),
    ]


def test_sqlite_replacement_lane_rebuilds_only_superseded_target(tmp_path: Path) -> None:
    uow_factory, ids, store, lane_store = _setup(tmp_path)
    with uow_factory().begin_immediate() as tx:
        slot = tx.connection.execute("SELECT id FROM slots").fetchone()
        target = tx.connection.execute(
            "SELECT st.id, st.channel_id FROM slot_targets st JOIN channels c ON c.id=st.channel_id "
            "WHERE c.channel_key='fb_hanoi'"
        ).fetchone()
        tx.packages.save(
            _package(
                str(slot["id"]),
                "package-old-synthetic",
                created_at_ms=NOW_MS - 121 * 24 * 60 * 60 * 1000,
            )
        )
        tx.deliveries.save(
            Delivery("delivery-superseded-synthetic", DeliveryState.SUPERSEDED),
            target_id=str(target["id"]),
            channel_id=str(target["channel_id"]),
            package_id="package-old-synthetic",
            created_at_ms=NOW_MS,
            updated_at_ms=NOW_MS,
        )
    package_factory = _PackageFactory(
        LanePackage("package-lane-synthetic", "topic-lane-synthetic"), uow_factory
    )
    runner = RunLanes(lane_store, package_factory, ReserveTarget(store, _Clock(), ids), _Clock())

    result = runner.run_replacement(horizon_days=1)

    assert len(result.reserved_target_ids) == 1
    with uow_factory().read_only() as tx:
        rows = tx.connection.execute(
            """SELECT d.state, c.channel_key FROM deliveries d
               JOIN channels c ON c.id=d.channel_id ORDER BY d.created_at, d.id"""
        ).fetchall()
    hanoi_states = [row["state"] for row in rows if row["channel_key"] == "fb_hanoi"]
    assert hanoi_states == ["SUPERSEDED", "DRAFT"]
    assert sum(row["channel_key"] == "fb_venho" for row in rows) == 0
    assert sum(row["channel_key"] == "ig_venho" for row in rows) == 0
