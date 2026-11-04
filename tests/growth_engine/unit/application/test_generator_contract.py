from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from growth_engine.adapters.outbound.legacy.fact_source import LegacyFactSource
from growth_engine.adapters.outbound.legacy.generator_adapter import LegacyGeneratorAdapter
from growth_engine.application.dto import DraftRequest


REPO_ROOT = Path(__file__).resolve().parents[4]


class FakeTextProvider:
    def __init__(self) -> None:
        self.calls = []

    def __call__(self, request, prompt, config):
        self.calls.append((request, prompt, config))
        return {
            "title": "Một buổi sáng bên Hồ Tây",
            "hook": "Một buổi sáng chậm bên Hồ Tây",
            "body": "Mặt hồ yên và ánh sáng dịu mở đầu ngày Hà Nội.",
            "cta": "Nhắn Ven Hồ để hỏi phòng phù hợp.",
            "hashtags": ["#venhohotelhanoi", "#hotay"],
        }


class FakeImageProvider:
    enabled = True
    model = "fake-image"

    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.calls = []

    def generate(self, prompt, *, size, quality, reference_images=None):
        self.calls.append((prompt, size, quality, reference_images))
        return self.payload


def _image_bytes(path: Path) -> bytes:
    Image.new("RGB", (32, 24), (30, 90, 120)).save(path, format="PNG")
    return path.read_bytes()


def _write_fact(root: Path, key: str, **overrides) -> None:
    facts_dir = root / "venho_hotel" / "growth" / "facts"
    facts_dir.mkdir(parents=True, exist_ok=True)
    safe_name = key.replace(".", "__")
    payload = {
        "fact_key": key,
        "value": "Ven Ho is beside West Lake",
        "status": "approved",
        "valid_from": "2026-01-01T00:00:00+00:00",
        "valid_to": None,
        **overrides,
    }
    (facts_dir / f"{safe_name}.json").write_text(json.dumps(payload), encoding="utf-8")


def test_generator_returns_contract_fields_and_keeps_images_temporary(tmp_path, monkeypatch):
    data_root = tmp_path / "data" / "projects"
    knowledge_dir = data_root / "venho_hotel" / "knowledge"
    knowledge_dir.mkdir(parents=True)
    shutil.copyfile(
        REPO_ROOT / "data/projects/venho_hotel/knowledge/VENHO_HOTEL_WESTLAKE_DNA.json",
        knowledge_dir / "VENHO_HOTEL_WESTLAKE_DNA.json",
    )
    publishing_dir = data_root / "venho_hotel" / "publishing"
    publishing_dir.mkdir(parents=True)
    sentinel = publishing_dir / "existing.json"
    sentinel.write_text('{"untouched": true}', encoding="utf-8")
    before = (sentinel.stat().st_mtime_ns, sentinel.read_bytes())

    assets_root = tmp_path / "assets"
    assets_root.mkdir()
    asset_path = assets_root / "reference.png"
    _image_bytes(asset_path)

    from agent_studio.growth.scenario_registry import ScenarioRegistry
    from agent_studio.growth.reference_asset_resolver import ReferenceAssetResolver

    registry = ScenarioRegistry.from_file(
        REPO_ROOT / "config/projects/venho_hotel/growth/scenario_registry.yaml"
    )
    mapping = {
        asset_id: "reference.png"
        for scenario in registry.scenarios.values()
        for asset_id in scenario.reference_asset_ids
    }
    resolver = ReferenceAssetResolver(mapping, assets_root=assets_root)
    text_provider = FakeTextProvider()
    image_provider = FakeImageProvider(asset_path.read_bytes())
    temp_root = tmp_path / "runtime-images"
    monkeypatch.setenv("GROWTH_IMAGE_ALTERNATIVES", "0")

    adapter = LegacyGeneratorAdapter(
        repo_root=REPO_ROOT,
        data_root=data_root,
        config_root=REPO_ROOT / "config/projects",
        scenario_registry=registry,
        reference_resolver=resolver,
        generator_fn=text_provider,
        image_provider=image_provider,
        temp_root=temp_root,
    )
    package = adapter.draft(
        DraftRequest(
            project_id="venho_hotel",
            slot_id="slot-contract-1",
            lane="monday",
            at_ms=1_799_000_000_000,
            facts={"topic": "sương sớm trên mặt hồ", "fact_keys": ["hotel.room_count"]},
        )
    )

    assert package.topic_key and package.pillar == "west_lake_life" and package.brief
    assert package.fact_keys == ("hotel.room_count",)
    assert package.captions_by_profile["default"] == (
        "Một buổi sáng chậm bên Hồ Tây\n\n"
        "Mặt hồ yên và ánh sáng dịu mở đầu ngày Hà Nội.\n\n"
        "Nhắn Ven Hồ để hỏi phòng phù hợp.\n\n#venhohotelhanoi #hotay"
    )
    assert len(text_provider.calls) == 1
    assert text_provider.calls[0][0].topic == "sương sớm trên mặt hồ"
    assert len(package.image_options) >= 1
    image_option = package.image_options[0]
    assert image_option["option_id"] == "A"
    assert Path(image_option["path"]).is_file()
    assert Path(image_option["path"]).is_relative_to(temp_root)
    assert image_option["provenance"]["scenario_key"] == "venho_west_lake_landscape"
    assert (sentinel.stat().st_mtime_ns, sentinel.read_bytes()) == before

    adapter.close()
    assert not Path(image_option["path"]).exists()


def test_fact_source_returns_only_approved_current_facts_and_is_read_only(tmp_path):
    data_root = tmp_path / "data" / "projects"
    _write_fact(data_root, "hotel.current", confidence=0.82)
    _write_fact(data_root, "hotel.pending", status="pending")
    _write_fact(data_root, "hotel.future", valid_from="2027-01-01T00:00:00+00:00")
    _write_fact(data_root, "hotel.expired", valid_to="2026-02-01T00:00:00+00:00")
    publishing_dir = data_root / "venho_hotel" / "publishing"
    publishing_dir.mkdir(parents=True)
    sentinel = publishing_dir / "existing.json"
    sentinel.write_text('{"untouched": true}', encoding="utf-8")
    before = (sentinel.stat().st_mtime_ns, sentinel.read_bytes())
    at_ms = int(datetime(2026, 6, 1, tzinfo=timezone.utc).timestamp() * 1000)

    snapshot = LegacyFactSource(data_root=data_root).approved_facts(
        ["hotel.expired", "hotel.current", "hotel.pending", "hotel.future", "hotel.missing"],
        at_ms,
    )

    assert list(snapshot.facts) == ["hotel.current"]
    assert snapshot.facts["hotel.current"]["status"] == "approved"
    assert len(snapshot.snapshot_hash) == 64
    assert snapshot.snapshot_hash == LegacyFactSource(data_root=data_root).approved_facts(
        ["hotel.missing", "hotel.future", "hotel.current", "hotel.pending", "hotel.expired"],
        at_ms,
    ).snapshot_hash
    assert (sentinel.stat().st_mtime_ns, sentinel.read_bytes()) == before


def test_fact_source_does_not_create_missing_fact_directory(tmp_path):
    data_root = tmp_path / "data" / "projects"
    facts_dir = data_root / "venho_hotel" / "growth" / "facts"
    snapshot = LegacyFactSource(data_root=data_root).approved_facts(["hotel.missing"], 1_800_000_000_000)

    assert snapshot.facts == {}
    assert len(snapshot.snapshot_hash) == 64
    assert not facts_dir.exists()
