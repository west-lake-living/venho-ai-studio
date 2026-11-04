from __future__ import annotations

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from growth_engine.adapters.outbound.persistence.sqlite.repositories.budget import BudgetRepository
from growth_engine.application.content.generate_package import (
    GeneratePackage,
    GeneratePackageCommand,
    GenerationClaim,
    GenerationUnknown,
    choose_default_image,
)
from growth_engine.application.dto import DraftPackage, DraftRequest, FactSnapshot
from growth_engine.domain.content.package import ContentPackage
from growth_engine.domain.kernel.errors import DomainError


class FakeClock:
    def now_ms(self):
        return 1_798_000_000_000


class SequentialIds:
    def __init__(self):
        self.value = 0

    def new_id(self):
        self.value += 1
        return f"id-{self.value}"


class FakeGenerator:
    image_provider = None

    def __init__(self, *, fail=False):
        self.calls = 0
        self.fail = fail

    def draft(self, request):
        self.calls += 1
        if self.fail:
            raise TimeoutError("synthetic provider timeout")
        return DraftPackage(
            topic_key="west_lake:morning-1234567890",
            pillar="west_lake_life",
            brief="A calm West Lake morning.",
            fact_keys=("hotel.room_count",),
            captions_by_profile={"default": "A calm morning by West Lake."},
            image_options=(
                {
                    "option_id": "A",
                    "path": str(self.image_path),
                    "provenance": {"source": "fake", "image_sha256": "a" * 64},
                },
            ),
        )


class FakeFactSource:
    def approved_facts(self, keys, at_ms):
        assert keys == ["hotel.room_count"]
        return FactSnapshot(
            {"hotel.room_count": {"fact_key": "hotel.room_count", "value": "15 rooms", "version": 3}},
            "b" * 64,
        )


class FakeAssetIngestor:
    def __init__(self):
        self.ids = []

    def execute(self, *, source_type, source_ref, source_revision, stream, metadata):
        assert stream.read()
        asset_id = f"asset-{len(self.ids) + 1}"
        self.ids.append((asset_id, source_type, source_ref, source_revision, metadata))
        return SimpleNamespace(id=asset_id)


class FakeGenerationStore:
    def __init__(self, *, cap=10_000):
        self.cap = cap
        self.reserved = 0
        self.states = {}
        self.unknown = []
        self.packages = []
        self.asset_options = []
        self.captions_by_profile = {}

    def claim_generation(self, business_key, *, estimated_cost_minor, **kwargs):
        current = self.states.get(business_key)
        if current == "UNKNOWN":
            return GenerationClaim("UNKNOWN")
        if current == "SUCCEEDED":
            return GenerationClaim("SUCCEEDED", self.packages[-1], ("delivery-page-a", "delivery-page-b"))
        if self.reserved + estimated_cost_minor > self.cap:
            self.states[business_key] = "BUDGET_EXCEEDED"
            return GenerationClaim("BUDGET_EXCEEDED")
        self.reserved += estimated_cost_minor
        self.states[business_key] = "RESERVED"
        return GenerationClaim("CLAIMED")

    def mark_generation_unknown(self, business_key, *, error_class, now_ms, correlation_id):
        self.states[business_key] = "UNKNOWN"
        self.unknown.append((business_key, error_class, now_ms))

    def complete_generation(
        self,
        business_key,
        package,
        asset_options,
        package_facts,
        captions_by_profile,
        *,
        settled_at_ms,
        estimated_cost_minor,
        correlation_id,
    ):
        self.states[business_key] = "SUCCEEDED"
        self.packages.append(package)
        self.asset_options.extend(asset_options)
        self.captions_by_profile = dict(captions_by_profile)
        return ("delivery-page-a", "delivery-page-b")


class FakeBudgetPolicy:
    monthly_cap_minor = 10_000
    currency = "VND"


def _write_image(path: Path) -> None:
    Image.new("RGB", (24, 24), (120, 80, 40)).save(path, format="PNG")


def _command():
    return GeneratePackageCommand(
        request=DraftRequest(
            project_id="venho_hotel",
            slot_id="slot-1",
            lane="monday",
            at_ms=1_798_000_000_000,
            facts={"fact_keys": ["hotel.room_count"]},
        ),
        package_spec_hash="c" * 64,
        generator_version="gc2-test-v1",
        lane="monday",
    )


def test_generate_package_persists_shared_package_and_two_draft_deliveries(tmp_path):
    image_path = tmp_path / "generated.png"
    _write_image(image_path)
    generator = FakeGenerator()
    generator.image_path = image_path
    store = FakeGenerationStore()
    assets = FakeAssetIngestor()
    use_case = GeneratePackage(
        store,
        generator,
        FakeFactSource(),
        assets,
        FakeClock(),
        SequentialIds(),
        budget_policy=FakeBudgetPolicy(),
        cost_estimates={"text_generation_minor": 5_000, "image_generation_minor": 1_200},
    )

    result = use_case.execute(_command())

    assert isinstance(result.package, ContentPackage)
    assert result.package.slot_id == "slot-1"
    assert result.package.topic_key == "west_lake:morning-1234567890"
    assert result.delivery_ids == ("delivery-page-a", "delivery-page-b")
    assert result.asset_ids == ("asset-1",)
    assert json.loads(result.package.fact_snapshot_json)["hotel.room_count"]["value"] == "15 rooms"
    from growth_engine.domain.kernel.hashing import sha256_hex

    assert result.package.fact_snapshot_hash == sha256_hex(result.package.fact_snapshot_json.encode("utf-8"))
    assert len(assets.ids) == 1
    assert store.captions_by_profile == {"default": "A calm morning by West Lake."}


def test_paid_generation_timeout_is_unknown_and_is_never_called_again():
    generator = FakeGenerator(fail=True)
    store = FakeGenerationStore()
    use_case = GeneratePackage(
        store,
        generator,
        FakeFactSource(),
        FakeAssetIngestor(),
        FakeClock(),
        SequentialIds(),
        budget_policy=FakeBudgetPolicy(),
        cost_estimates={"text_generation_minor": 5_000, "image_generation_minor": 1_200},
    )

    with pytest.raises(GenerationUnknown):
        use_case.execute(_command())
    with pytest.raises(GenerationUnknown):
        use_case.execute(_command())

    assert generator.calls == 1
    assert len(store.unknown) == 1
    assert store.states[next(iter(store.states))] == "UNKNOWN"


def test_budget_exceeded_blocks_before_calling_generator():
    generator = FakeGenerator()
    store = FakeGenerationStore(cap=1)
    use_case = GeneratePackage(
        store,
        generator,
        FakeFactSource(),
        FakeAssetIngestor(),
        FakeClock(),
        SequentialIds(),
        budget_policy=FakeBudgetPolicy(),
        cost_estimates={"text_generation_minor": 5_000, "image_generation_minor": 1_200},
    )

    with pytest.raises(DomainError) as raised:
        use_case.execute(_command())

    assert raised.value.code == "ERR_GC2_BUDGET_EXCEEDED"
    assert generator.calls == 0


def test_budget_reservation_is_atomic_across_two_concurrent_jobs(tmp_path):
    database = tmp_path / "budget.db"
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        connection.executescript(
            """
            CREATE TABLE paid_calls (
              id TEXT PRIMARY KEY, business_key TEXT NOT NULL UNIQUE,
              period_key TEXT NOT NULL, currency TEXT NOT NULL,
              provider TEXT NOT NULL, operation TEXT NOT NULL,
              state TEXT NOT NULL, reserved_minor INTEGER NOT NULL,
              actual_minor INTEGER, external_job_id TEXT,
              created_at INTEGER NOT NULL, settled_at INTEGER
            );
            """
        )

    def reserve(index):
        connection = sqlite3.connect(database, timeout=5, isolation_level=None)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("BEGIN IMMEDIATE")
            accepted = BudgetRepository(connection).reserve(
                call_id=f"call-{index}",
                business_key=f"job-{index}",
                period_key="2026-11",
                currency="VND",
                provider="test",
                operation="generation",
                amount_minor=70,
                cap_minor=100,
                created_at_ms=1,
            )
            connection.commit()
            return accepted
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        accepted = list(pool.map(reserve, (1, 2)))

    assert sorted(accepted) == [False, True]
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT SUM(reserved_minor) FROM paid_calls").fetchone()[0] == 70


def test_fallback_is_selected_only_after_ai_and_library_qc_fail():
    options = (
        {"option_id": "A", "path": "/tmp/a.png"},
        {"option_id": "C", "path": "/tmp/c.jpg"},
        {"option_id": "FALLBACK", "path": "/tmp/fallback.jpg"},
    )

    assert choose_default_image(options, {"A": "FAIL", "C": "PASS"})["option_id"] == "C"
    assert choose_default_image(options, {"A": "FAIL", "C": "FAIL"})["label"] == "Ảnh dự phòng"
    assert choose_default_image(options, {"A": "REVIEW", "C": "FAIL"}) is None
