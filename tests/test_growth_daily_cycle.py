from __future__ import annotations

import json
from pathlib import Path
from shutil import copyfile

from agent_studio.growth.reference_asset_resolver import ReferenceAssetResolver
from image_studio_runtime.adapters.mock_image_provider import MockImageProvider
from publishing_gateway.publication_registry import PublicationRegistry

from growth_orchestrator.application.daily_cycle import (
    DEFAULT_PLATFORMS,
    _pick_topic,
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


def test_run_daily_cycle_saturday_runs_real_special_lane_fallback_selection(tmp_path: Path) -> None:
    """DoD #10: the Saturday topic must go through the real loai-4 fallback
    selection (special_lane.select_special_lane_candidate), not just a
    rotation index. With no live trend/event feed, every candidate defaults
    to type feature_story (loai 4) and selected_reason must say so."""
    data_root = _tmp_data_root(tmp_path)
    result = run_daily_cycle("saturday", platforms=["facebook"], data_root=data_root, generate_image=False)
    assert result.topic["special_lane_type"] == "feature_story"
    assert result.topic["special_lane_reason"] == "feature_story"


def test_pick_topic_special_lane_prefers_seasonal_over_feature_story(tmp_path: Path) -> None:
    """Priority order proof: if a group is tagged type=seasonal_nature, the
    fallback logic must pick it over the feature_story default -- confirms
    the wiring is a real priority selection, not a no-op passthrough."""
    config = {
        "content_pillars": {
            "special_topics": [
                {"id": "a", "name": "Feature", "dna_subject": "outside", "topics": ["t1"]},
            ]
        }
    }
    data_root = _tmp_data_root(tmp_path)
    picked = _pick_topic(config, "saturday", "venho_hotel", data_root)
    assert picked["special_lane_type"] == "feature_story"

    config["content_pillars"]["special_topics"][0]["type"] = "seasonal_nature"
    picked2 = _pick_topic(config, "saturday", "venho_hotel", data_root)
    assert picked2["special_lane_type"] == "seasonal_nature"
    assert picked2["special_lane_reason"] == "seasonal_nature"


def test_pick_topic_special_lane_rejects_unverified_cultural_event(tmp_path: Path) -> None:
    """Eligibility guard: a cultural_event candidate without
    verified_by_human=true must not be selectable -- with no other type
    available, select_special_lane_candidate must raise rather than silently
    let an unverified event through."""
    config = {
        "content_pillars": {
            "special_topics": [
                {"id": "a", "name": "Event", "dna_subject": "outside", "topics": ["t1"], "type": "cultural_event"},
            ]
        }
    }
    data_root = _tmp_data_root(tmp_path)
    try:
        _pick_topic(config, "saturday", "venho_hotel", data_root)
        assert False, "expected ValueError for unverified cultural_event with no feature_story fallback"
    except ValueError as exc:
        assert "feature_story" in str(exc)


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

    # DoD #7: approval snapshot must reference the real generated image's
    # run_id as its asset version, not an empty list.
    asset_version_ids = result.publications[0]["package_snapshot"]["asset_version_ids"]
    assert asset_version_ids == [Path(image_path).name]

    # DoD #5: cross-modal (image-vs-DNA) validation must actually run and be
    # persisted next to the generated artifact -- not skipped.
    report = json.loads((Path(image_path) / "image_validation_report.json").read_text(encoding="utf-8"))
    assert report["kill_switch"]["triggered"] is False
    assert report["verdict"]


def test_generate_topic_image_discards_image_on_kill_switch(tmp_path: Path, monkeypatch) -> None:
    """A high-severity forbidden violation from the DNA-match validator must
    discard the generated image (same as a generation failure) rather than
    queuing a brand-unsafe photo for approval."""
    import growth_orchestrator.application.daily_cycle as daily_cycle_module

    class _FakeKillSwitch:
        triggered = True

    class _FakeReport:
        kill_switch = _FakeKillSwitch()

        def model_dump_json(self, indent=2):
            return "{}"

    monkeypatch.setattr(daily_cycle_module, "validate_image", lambda *a, **k: _FakeReport())

    data_root = _tmp_data_root(tmp_path)
    provider = MockImageProvider()
    resolver = ReferenceAssetResolver({}, assets_root=Path("."))

    result = run_daily_cycle(
        "monday", platforms=["facebook"], data_root=data_root, image_provider=provider, reference_resolver=resolver
    )

    assert result.publications[0]["content"]["image_run_path"] is None
    assert result.publications[0]["package_snapshot"]["asset_version_ids"] == []


def test_run_daily_cycle_asset_version_ids_empty_when_image_generation_disabled(tmp_path: Path) -> None:
    data_root = _tmp_data_root(tmp_path)
    result = run_daily_cycle("monday", platforms=["facebook"], data_root=data_root, generate_image=False)
    assert result.publications[0]["package_snapshot"]["asset_version_ids"] == []


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
