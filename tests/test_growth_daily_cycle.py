from __future__ import annotations

from pathlib import Path
from shutil import copyfile

from agent_studio.growth.reference_asset_resolver import ReferenceAssetResolver
from image_studio_runtime.adapters.mock_image_provider import MockImageProvider
from publishing_gateway.publication_registry import PublicationRegistry

from growth_orchestrator.application.daily_cycle import (
    DEFAULT_PLATFORMS,
    run_daily_cycle,
)


def _tmp_data_root(tmp_path: Path) -> Path:
    root = tmp_path / "data" / "projects"
    knowledge_dir = root / "venho_hotel" / "knowledge"
    knowledge_dir.mkdir(parents=True)
    for name in ["VENHO_HOTEL_WESTLAKE_DNA.json", "VENHO_HOTEL_LAKE_VIEW_ROOM_DNA.json", "VENHO_HOTEL_OUTSIDE_DNA.json"]:
        copyfile(Path("data/projects/venho_hotel/knowledge") / name, knowledge_dir / name)
    return root


def test_run_daily_cycle_rejects_non_cadence_day(tmp_path: Path) -> None:
    try:
        run_daily_cycle("tuesday", data_root=_tmp_data_root(tmp_path))
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "cadence day" in str(exc)


def test_run_daily_cycle_queues_one_pending_approval_publication_per_platform(tmp_path: Path) -> None:
    data_root = _tmp_data_root(tmp_path)
    result = run_daily_cycle("monday", data_root=data_root, generate_image=False)

    assert result.day == "monday"
    assert result.topic["dna_subject"] == "westlake"
    assert [pub["platform"] for pub in result.publications] == DEFAULT_PLATFORMS
    for pub in result.publications:
        assert pub["status"] == "PENDING_APPROVAL"
        assert pub["content"]["text"]

    registry = PublicationRegistry("venho_hotel", data_root=data_root)
    stored = registry.load()["publications"]
    assert len(stored) == len(DEFAULT_PLATFORMS)


def test_run_daily_cycle_saturday_uses_special_topics(tmp_path: Path) -> None:
    data_root = _tmp_data_root(tmp_path)
    result = run_daily_cycle("saturday", platforms=["facebook"], data_root=data_root, generate_image=False)
    assert result.topic["dna_subject"] == "outside"
    assert result.topic["pillar"] == "Cuoi tuan o Tay Ho"


def test_run_daily_cycle_rotation_advances_across_calls(tmp_path: Path) -> None:
    data_root = _tmp_data_root(tmp_path)
    first = run_daily_cycle("monday", platforms=["facebook"], data_root=data_root, generate_image=False)
    second = run_daily_cycle("monday", platforms=["facebook"], data_root=data_root, generate_image=False)
    assert first.topic["topic"] != second.topic["topic"]


def test_run_daily_cycle_skips_image_generation_when_disabled(tmp_path: Path) -> None:
    data_root = _tmp_data_root(tmp_path)
    result = run_daily_cycle("monday", platforms=["facebook"], data_root=data_root, generate_image=False)
    assert result.publications[0]["content"]["image_run_path"] is None


def test_run_daily_cycle_saturday_generates_real_image_with_injected_provider(tmp_path: Path) -> None:
    data_root = _tmp_data_root(tmp_path)
    provider = MockImageProvider()
    resolver = ReferenceAssetResolver(
        {"venho_rooftop_railing_approved": "assets/raw/outside/IMG_5125.jpg"},
        assets_root=Path("."),
    )

    result = run_daily_cycle(
        "saturday", platforms=["facebook"], data_root=data_root, image_provider=provider, reference_resolver=resolver
    )

    assert provider.calls == 1
    image_path = result.publications[0]["content"]["image_run_path"]
    assert image_path is not None
    assert (Path(image_path) / "manifest.json").exists()


def test_run_daily_cycle_monday_has_no_reference_asset_but_still_generates(tmp_path: Path) -> None:
    # westlake's scenario (venho_west_lake_landscape) has reference_mode: none
    # -- text-to-image only, no reference asset lookup should happen.
    data_root = _tmp_data_root(tmp_path)
    provider = MockImageProvider()
    resolver = ReferenceAssetResolver({}, assets_root=Path("."))

    result = run_daily_cycle(
        "monday", platforms=["facebook"], data_root=data_root, image_provider=provider, reference_resolver=resolver
    )

    assert provider.calls == 1
    assert result.publications[0]["content"]["image_run_path"] is not None
