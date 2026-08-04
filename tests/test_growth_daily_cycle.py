from __future__ import annotations

import json
from pathlib import Path
from shutil import copyfile

from agent_studio.growth.reference_asset_resolver import ReferenceAssetResolver
from content_studio.builders.social_builder import mock_social_generator
from image_studio_runtime.adapters.mock_image_provider import MockImageProvider
from publishing_gateway.publication_registry import PublicationRegistry

from growth_orchestrator.application.daily_cycle import (
    DEFAULT_PLATFORMS,
    _pick_topic,
    run_daily_cycle,
)
from growth_orchestrator.bridges.m05_content_bridge import M05ContentBridge


class _AlwaysApproveValidatorBridge:
    """Bypasses M03ValidatorBridge's real content-scoring rubric.

    mock_social_generator's boilerplate text reliably scores below the real
    APPROVE bar (see validator_studio.content_validator), which would make
    daily_cycle's retry loop burn through MAX_TEXT_ATTEMPTS and then drop
    the publication -- these tests are about the daily_cycle/image/rotation
    plumbing, not content-quality scoring, so they inject this instead.
    """

    def validate_package(self, brief: dict, copy_candidate: dict) -> dict:
        return {"verdict": "READY_FOR_REVIEW", "reports": []}


def _tmp_data_root(tmp_path: Path) -> Path:
    root = tmp_path / "data" / "projects"
    knowledge_dir = root / "venho_hotel" / "knowledge"
    knowledge_dir.mkdir(parents=True)
    for name in ["VENHO_HOTEL_WESTLAKE_DNA.json", "VENHO_HOTEL_LAKE_VIEW_ROOM_DNA.json", "VENHO_HOTEL_OUTSIDE_DNA.json"]:
        copyfile(Path("data/projects/venho_hotel/knowledge") / name, knowledge_dir / name)
    return root


def _mock_content_bridge(data_root: Path) -> M05ContentBridge:
    """M05ContentBridge with a mock generator -- avoids billed Claude API
    calls in tests (default generator_fn is the real gpt_social_generator)."""
    return M05ContentBridge(data_root=data_root, generator_fn=mock_social_generator)


def test_run_daily_cycle_rejects_non_cadence_day(tmp_path: Path) -> None:
    data_root = _tmp_data_root(tmp_path)
    try:
        run_daily_cycle("tuesday", data_root=data_root, content_bridge=_mock_content_bridge(data_root), validator_bridge=_AlwaysApproveValidatorBridge())
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "cadence day" in str(exc)


def test_run_daily_cycle_queues_one_pending_approval_publication_per_platform(tmp_path: Path) -> None:
    data_root = _tmp_data_root(tmp_path)
    result = run_daily_cycle("monday", data_root=data_root, generate_image=False, content_bridge=_mock_content_bridge(data_root), validator_bridge=_AlwaysApproveValidatorBridge())

    assert result.day == "monday"
    assert result.topic["dna_subject"] == "westlake"
    assert [pub["platform"] for pub in result.publications] == DEFAULT_PLATFORMS
    for pub in result.publications:
        assert pub["status"] == "PENDING_APPROVAL"
        assert pub["content"]["text"]

    registry = PublicationRegistry("venho_hotel", data_root=data_root)
    stored = registry.load()["publications"]
    assert len(stored) == len(DEFAULT_PLATFORMS)


def test_run_daily_cycle_one_platform_failure_does_not_abort_the_others(tmp_path: Path) -> None:
    """A provider blip on one platform (rate limit, network) must not drop the
    other platforms' drafts for the same day -- regression test for the
    previously-unguarded per-platform loop in run_daily_cycle."""
    data_root = _tmp_data_root(tmp_path)

    class _FlakyOnInstagramBridge:
        def __init__(self, real_bridge: M05ContentBridge) -> None:
            self._real_bridge = real_bridge

        def generate_candidates(self, brief: dict) -> list[dict]:
            if brief["platforms"] == ["instagram"]:
                raise RuntimeError("simulated OpenAI rate limit")
            return self._real_bridge.generate_candidates(brief)

    result = run_daily_cycle(
        "monday",
        data_root=data_root,
        generate_image=False,
        content_bridge=_FlakyOnInstagramBridge(_mock_content_bridge(data_root)),
        validator_bridge=_AlwaysApproveValidatorBridge(),
    )

    succeeded_platforms = [pub["platform"] for pub in result.publications]
    assert "instagram" not in succeeded_platforms
    assert set(DEFAULT_PLATFORMS) - {"instagram"} <= set(succeeded_platforms)
    assert result.errors == [{"platform": "instagram", "error": "RuntimeError: simulated OpenAI rate limit"}]


def test_run_daily_cycle_saturday_uses_special_topics(tmp_path: Path) -> None:
    data_root = _tmp_data_root(tmp_path)
    result = run_daily_cycle("saturday", platforms=["facebook"], data_root=data_root, generate_image=False, content_bridge=_mock_content_bridge(data_root), validator_bridge=_AlwaysApproveValidatorBridge())
    assert result.topic["dna_subject"] == "outside"
    assert result.topic["pillar"] == "Cuoi tuan o Tay Ho"


def test_run_daily_cycle_saturday_runs_real_special_lane_fallback_selection(tmp_path: Path) -> None:
    """DoD #10: the Saturday topic must go through the real loai-4 fallback
    selection (special_lane.select_special_lane_candidate), not just a
    rotation index. With no live trend/event feed, every candidate defaults
    to type feature_story (loai 4) and selected_reason must say so."""
    data_root = _tmp_data_root(tmp_path)
    result = run_daily_cycle("saturday", platforms=["facebook"], data_root=data_root, generate_image=False, content_bridge=_mock_content_bridge(data_root), validator_bridge=_AlwaysApproveValidatorBridge())
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
    first = run_daily_cycle("monday", platforms=["facebook"], data_root=data_root, generate_image=False, content_bridge=_mock_content_bridge(data_root), validator_bridge=_AlwaysApproveValidatorBridge())
    second = run_daily_cycle("monday", platforms=["facebook"], data_root=data_root, generate_image=False, content_bridge=_mock_content_bridge(data_root), validator_bridge=_AlwaysApproveValidatorBridge())
    assert first.topic["topic"] != second.topic["topic"]


def test_run_daily_cycle_skips_image_generation_when_disabled(tmp_path: Path) -> None:
    data_root = _tmp_data_root(tmp_path)
    result = run_daily_cycle("monday", platforms=["facebook"], data_root=data_root, generate_image=False, content_bridge=_mock_content_bridge(data_root), validator_bridge=_AlwaysApproveValidatorBridge())
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
    , content_bridge=_mock_content_bridge(data_root), validator_bridge=_AlwaysApproveValidatorBridge())

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


def test_run_daily_cycle_uploads_validated_image_to_drive_and_stores_public_url(tmp_path: Path) -> None:
    """Regression test: a validated image used to only be stored as a local
    image_run_path, which Make.com's webhook payload never actually used --
    generated photos never reached the real post. Now upload_and_publish is
    called and its URL lands in content.image_public_url."""
    from shared.storage.google_drive import MockDriveUploader

    data_root = _tmp_data_root(tmp_path)
    provider = MockImageProvider()
    resolver = ReferenceAssetResolver(
        {"venho_rooftop_railing_approved": "assets/raw/outside/IMG_5125.jpg"},
        assets_root=Path("."),
    )
    uploader = MockDriveUploader()

    result = run_daily_cycle(
        "saturday",
        platforms=["facebook"],
        data_root=data_root,
        image_provider=provider,
        reference_resolver=resolver,
        drive_uploader=uploader,
        content_bridge=_mock_content_bridge(data_root),
        validator_bridge=_AlwaysApproveValidatorBridge(),
    )

    assert len(uploader.uploads) == 1
    public_url = result.publications[0]["content"]["image_public_url"]
    assert public_url is not None
    assert public_url.startswith("https://drive.google.com/")


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
    , content_bridge=_mock_content_bridge(data_root), validator_bridge=_AlwaysApproveValidatorBridge())

    assert result.publications[0]["content"]["image_run_path"] is None
    assert result.publications[0]["package_snapshot"]["asset_version_ids"] == []


def test_run_daily_cycle_asset_version_ids_empty_when_image_generation_disabled(tmp_path: Path) -> None:
    data_root = _tmp_data_root(tmp_path)
    result = run_daily_cycle("monday", platforms=["facebook"], data_root=data_root, generate_image=False, content_bridge=_mock_content_bridge(data_root), validator_bridge=_AlwaysApproveValidatorBridge())
    assert result.publications[0]["package_snapshot"]["asset_version_ids"] == []


def test_run_daily_cycle_monday_has_no_reference_asset_but_still_generates(tmp_path: Path, monkeypatch) -> None:
    # westlake's scenario (venho_west_lake_landscape) has reference_mode: none
    # -- text-to-image only, no reference asset lookup should happen.
    import growth_orchestrator.application.daily_cycle as daily_cycle_module

    class _FakeKillSwitch:
        triggered = False

    class _FakeReport:
        kill_switch = _FakeKillSwitch()
        verdict = daily_cycle_module.Recommendation.APPROVE

        def model_dump_json(self, indent=2):
            return "{}"

    # This test is about the reference-asset-less image path, not the mock
    # vision observer's score against westlake's DNA -- stub validate_image
    # to always approve so it isn't at the mercy of that unrelated score.
    monkeypatch.setattr(daily_cycle_module, "validate_image", lambda *a, **k: _FakeReport())

    data_root = _tmp_data_root(tmp_path)
    provider = MockImageProvider()
    resolver = ReferenceAssetResolver({}, assets_root=Path("."))

    result = run_daily_cycle(
        "monday", platforms=["facebook"], data_root=data_root, image_provider=provider, reference_resolver=resolver
    , content_bridge=_mock_content_bridge(data_root), validator_bridge=_AlwaysApproveValidatorBridge())

    assert provider.calls == 1
    assert result.publications[0]["content"]["image_run_path"] is not None


def test_run_daily_cycle_saturday_reaches_generator_with_saturday_trend_lane(tmp_path: Path) -> None:
    """The Saturday special-lane brief must flag lane="saturday_trend" all
    the way through to the content generator, so gpt_social_generator can
    pick the weekend-events brief instead of the daily hotel brief."""
    data_root = _tmp_data_root(tmp_path)
    seen_requests = []

    def recording_generator(request, prompt, config):
        seen_requests.append(request)
        return mock_social_generator(request, prompt, config)

    bridge = M05ContentBridge(data_root=data_root, generator_fn=recording_generator)
    run_daily_cycle("saturday", platforms=["facebook"], data_root=data_root, generate_image=False, content_bridge=bridge, validator_bridge=_AlwaysApproveValidatorBridge())

    assert len(seen_requests) == 1
    assert seen_requests[0].lane == "saturday_trend"


def test_run_daily_cycle_monday_reaches_generator_with_daily_lane(tmp_path: Path) -> None:
    data_root = _tmp_data_root(tmp_path)
    seen_requests = []

    def recording_generator(request, prompt, config):
        seen_requests.append(request)
        return mock_social_generator(request, prompt, config)

    bridge = M05ContentBridge(data_root=data_root, generator_fn=recording_generator)
    run_daily_cycle("monday", platforms=["facebook"], data_root=data_root, generate_image=False, content_bridge=bridge, validator_bridge=_AlwaysApproveValidatorBridge())

    assert len(seen_requests) == 1
    assert seen_requests[0].lane == "daily"
    assert seen_requests[0].verified_events == []
    assert seen_requests[0].dna_subject == "westlake"
