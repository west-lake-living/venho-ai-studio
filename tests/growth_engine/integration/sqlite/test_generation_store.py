from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from threading import Lock
from uuid import uuid4

import pytest

from growth_engine.adapters.outbound.persistence.sqlite.connection import connect
from growth_engine.adapters.outbound.persistence.sqlite.generation_store import SqliteGenerationStore
from growth_engine.adapters.outbound.persistence.sqlite.migrator import MigrationRunner
from growth_engine.adapters.outbound.persistence.sqlite.uow import SqliteUnitOfWork
from growth_engine.application.content.generate_package import (
    GeneratePackage,
    GeneratePackageCommand,
    GenerationUnknown,
)
from growth_engine.application.scheduling.reserve_target import ReserveTarget, TargetAlreadyReserved
from growth_engine.application.dto import DraftPackage, DraftRequest, FactSnapshot
from growth_engine.application.scheduling.ensure_slots import EnsureSlots
from growth_engine.domain.kernel.errors import ErrorCode
from growth_engine.domain.kernel.hashing import sha256_hex
from growth_engine.domain.content.package import ContentPackage
from growth_engine.domain.scheduling.cadence import CadencePolicy, CadenceRule
from growth_engine.bootstrap import build_container
from growth_engine.settings import Settings


class _Clock:
    def now_ms(self) -> int:
        return 1_798_000_000_000


class _Ids:
    def new_id(self) -> str:
        return str(uuid4())


class _Generator:
    image_provider = None

    def __init__(self) -> None:
        self.calls = 0
        self.lock = Lock()

    def draft(self, request: DraftRequest) -> DraftPackage:
        with self.lock:
            self.calls += 1
            number = self.calls
        return DraftPackage(
            topic_key=f"west-lake-topic-{number}",
            pillar="west_lake_life",
            brief="Synthetic West Lake brief.",
            fact_keys=(),
            captions_by_profile={"default": "Synthetic approved caption."},
        )


class _TimeoutGenerator:
    image_provider = None

    def __init__(self) -> None:
        self.calls = 0

    def draft(self, request: DraftRequest) -> DraftPackage:
        self.calls += 1
        raise TimeoutError("synthetic provider timeout")


class _Facts:
    def approved_facts(self, keys, at_ms):
        return FactSnapshot({}, sha256_hex(b"{}"))


class _NoAssets:
    def execute(self, **kwargs):
        raise AssertionError("fixture has no image assets")


class _Budget:
    currency = "TEST"

    def __init__(self, cap: int) -> None:
        self.monthly_cap_minor = cap


def _setup(tmp_path: Path):
    database = tmp_path / "generation.sqlite"
    connection = connect(database)
    try:
        MigrationRunner(Path("growth_engine/adapters/outbound/persistence/sqlite/migrations")).apply(
            connection, application_version="generation-store-integration"
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
    store = SqliteGenerationStore(uow_factory, _Ids())
    return database, uow_factory, store


def _policy() -> CadencePolicy:
    return CadencePolicy(
        version=2,
        project_id="venho_hotel",
        timezone="Asia/Ho_Chi_Minh",
        publish_time="09:00",
        rules=(CadenceRule(0, "regular", "regular"),),
    )


def _command(slot_id: str, suffix: str = "a") -> GeneratePackageCommand:
    return GeneratePackageCommand(
        request=DraftRequest(
            project_id="venho_hotel", slot_id=slot_id, lane="regular",
            at_ms=1_798_000_000_000, facts={},
        ),
        package_spec_hash=suffix * 64,
        generator_version="synthetic-v1",
        lane="regular",
    )


def _use_case(store, generator, *, cap: int) -> GeneratePackage:
    return GeneratePackage(
        store, generator, _Facts(), _NoAssets(), _Clock(), _Ids(),
        budget_policy=_Budget(cap), cost_estimates={"text_generation_minor": 70},
    )


def test_sqlite_generation_persists_three_channel_targets_and_replays(tmp_path: Path) -> None:
    _, uow_factory, store = _setup(tmp_path)
    ensured = EnsureSlots(store, _Clock(), _Ids()).execute(
        _policy(), start_date=date(2026, 11, 2), horizon_days=1,
        environment="test", correlation_id="synthetic-generation",
    )
    assert ensured.slots_created == 1
    assert ensured.targets_created == 3
    assert set(ensured.unconfigured_channel_ids) == {
        "channel-fb_hanoi", "channel-fb_venho", "channel-ig_venho"
    }
    assert EnsureSlots(store, _Clock(), _Ids()).execute(
        _policy(), start_date=date(2026, 11, 2), horizon_days=1,
        environment="test", correlation_id="synthetic-generation-replay",
    ).targets_created == 0

    with uow_factory().read_only() as tx:
        slot_id = str(tx.connection.execute("SELECT id FROM slots").fetchone()[0])
    generator = _Generator()
    use_case = _use_case(store, generator, cap=1_000)
    command = _command(slot_id)
    first = use_case.execute(command)
    replay = use_case.execute(command)

    assert len(first.delivery_ids) == 3
    assert replay.replayed is True
    assert replay.delivery_ids == first.delivery_ids
    assert generator.calls == 1
    with uow_factory().read_only() as tx:
        targets = tx.connection.execute(
            "SELECT c.channel_key, d.state FROM deliveries d "
            "JOIN channels c ON c.id=d.channel_id ORDER BY c.channel_key"
        ).fetchall()
        jobs = tx.connection.execute(
            "SELECT kind, state FROM jobs ORDER BY kind"
        ).fetchall()
        paid = tx.budget.get(f"generate:{slot_id}:{'a' * 64}:synthetic-v1")
    assert [(row["channel_key"], row["state"]) for row in targets] == [
        ("fb_hanoi", "DRAFT"), ("fb_venho", "DRAFT"), ("ig_venho", "DRAFT")
    ]
    assert [row["kind"] for row in jobs] == ["assemble_revision"] * 3 + ["generate_package"]
    assert paid["state"] == "SETTLED"


def test_parallel_generation_claims_cannot_exceed_sqlite_budget(tmp_path: Path) -> None:
    _, uow_factory, store = _setup(tmp_path)
    EnsureSlots(store, _Clock(), _Ids()).execute(
        _policy(), start_date=date(2026, 11, 2), horizon_days=1,
        environment="test", correlation_id="synthetic-budget",
    )
    with uow_factory().read_only() as tx:
        slot_id = str(tx.connection.execute("SELECT id FROM slots").fetchone()[0])
    generators = (_Generator(), _Generator())
    cases = tuple(_use_case(store, generator, cap=100) for generator in generators)

    def execute(index: int):
        try:
            return cases[index].execute(_command(slot_id, "a" if index == 0 else "b"))
        except Exception as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(execute, (0, 1)))
    assert sum(not isinstance(result, Exception) for result in results) == 1
    errors = [result for result in results if isinstance(result, Exception)]
    assert len(errors) == 1
    assert getattr(errors[0], "code", None) == ErrorCode.BUDGET_EXCEEDED
    assert sum(generator.calls for generator in generators) == 1
    with uow_factory().read_only() as tx:
        total = tx.connection.execute(
            "SELECT COALESCE(SUM(COALESCE(actual_minor, reserved_minor)), 0) FROM paid_calls "
            "WHERE state IN ('RESERVED','UNKNOWN','SETTLED')"
        ).fetchone()[0]
    assert total == 70


def test_bootstrap_exposes_sqlite_generation_store(tmp_path: Path) -> None:
    database, _, _ = _setup(tmp_path)
    container = build_container(Settings(
        env="test",
        db_path=str(database),
        media_root=str(tmp_path / "media"),
        public_base_url="https://test.example.invalid",
        capability_keys="REQUIRED_FROM_P0",
        service_tokens="REQUIRED_FROM_P0",
    ))
    result = EnsureSlots(container.generation_store, _Clock(), _Ids()).execute(
        _policy(), start_date=date(2026, 11, 2), horizon_days=1,
        environment="test", correlation_id="bootstrap-generation-store",
    )
    assert result.targets_created == 3


def test_sqlite_generation_timeout_is_unknown_and_not_retried(tmp_path: Path) -> None:
    _, uow_factory, store = _setup(tmp_path)
    EnsureSlots(store, _Clock(), _Ids()).execute(
        _policy(), start_date=date(2026, 11, 2), horizon_days=1,
        environment="test", correlation_id="generation-timeout",
    )
    with uow_factory().read_only() as tx:
        slot_id = str(tx.connection.execute("SELECT id FROM slots").fetchone()[0])
    generator = _TimeoutGenerator()
    use_case = _use_case(store, generator, cap=1_000)
    command = _command(slot_id)
    with pytest.raises(GenerationUnknown):
        use_case.execute(command)
    with pytest.raises(GenerationUnknown):
        use_case.execute(command)
    assert generator.calls == 1
    with uow_factory().read_only() as tx:
        job = tx.connection.execute("SELECT state FROM jobs WHERE kind='generate_package'").fetchone()
        paid = tx.connection.execute("SELECT state FROM paid_calls").fetchone()
        incidents = tx.connection.execute("SELECT type FROM incidents").fetchall()
    assert job["state"] == "UNKNOWN"
    assert paid["state"] == "UNKNOWN"
    assert [row["type"] for row in incidents].count("GENERATION_UNKNOWN") == 1


def test_sqlite_reserve_target_blocks_second_active_delivery(tmp_path: Path) -> None:
    _, uow_factory, store = _setup(tmp_path)
    EnsureSlots(store, _Clock(), _Ids()).execute(
        _policy(), start_date=date(2026, 11, 2), horizon_days=1,
        environment="test", correlation_id="reserve-target",
    )
    with uow_factory().begin_immediate() as tx:
        slot = tx.connection.execute("SELECT id FROM slots").fetchone()
        target = tx.connection.execute("SELECT id FROM slot_targets ORDER BY id LIMIT 1").fetchone()
        tx.packages.save(ContentPackage(
            id="package-synthetic-reserve", slot_id=str(slot["id"]),
            topic_key="synthetic-reserve-topic", pillar="west_lake_life", lane="regular",
            source_snapshot_json='{"_synthetic":true}', fact_snapshot_json="{}",
            fact_snapshot_hash=sha256_hex(b"{}"), generation_version="synthetic-v1",
            created_at_ms=1_798_000_000_000,
        ))
    reserver = ReserveTarget(store, _Clock(), _Ids())
    created = reserver.execute(
        str(target["id"]), package_id="package-synthetic-reserve", lane="regular",
        correlation_id="reserve-first",
    )
    assert created.state.value == "DRAFT"
    with pytest.raises(TargetAlreadyReserved):
        reserver.execute(
            str(target["id"]), package_id="package-synthetic-reserve", lane="regular",
            correlation_id="reserve-replay",
        )
    with uow_factory().read_only() as tx:
        deliveries = tx.connection.execute(
            "SELECT count(*) FROM deliveries WHERE target_id=? AND active=1", (target["id"],)
        ).fetchone()[0]
    assert deliveries == 1
