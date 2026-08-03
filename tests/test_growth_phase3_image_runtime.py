from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_studio.growth.scenario_registry import ScenarioRegistry
from image_studio_runtime.adapters.mock_image_provider import MockImageProvider
from image_studio_runtime.application.generate_image import generate_image_run
from image_studio_runtime.application.repair_image import repair_image_run
from image_studio_runtime.domain.image_run import ImageRun
from image_studio_runtime.domain.quality_router import aggregate_image_verdict
from image_studio_runtime.storage.run_store import RunStore
from validator_studio.alignment_validator import validate_alignment
from validator_studio.derivative_validator import validate_derivatives


def _prompt_contract() -> dict:
    return {
        "schema_version": "1.0",
        "creative_brief_id": "brief-p3-001",
        "scenario_key": "venho_rooftop_sunrise",
        "base_prompt": "A warm rooftop breakfast scene at Ven Ho Hotel.",
        "size": "1024x1280",
        "quality": "high",
    }


def test_scenario_registry_resolves_visual_dna_and_rejects_conflict() -> None:
    registry = ScenarioRegistry.from_file()
    profile = registry.resolve("venho_rooftop_sunrise")

    assert profile.dna_subject == "outside"
    assert profile.dna_version == "2.7"
    assert "rooftop_railing" in profile.required_entities
    assert profile.reference_asset_ids == ("venho_rooftop_railing_approved",)

    with pytest.raises(ValueError, match="Scenario entity conflict"):
        registry.resolve("venho_rooftop_sunrise", forbidden_entities=["rooftop_railing"])


def test_mock_generation_creates_complete_immutable_manifest(tmp_path: Path) -> None:
    run_folder = generate_image_run(_prompt_contract(), content_package_id="pkg-p3-001", data_root=tmp_path, paid=True)
    manifest = json.loads((run_folder / "manifest.json").read_text(encoding="utf-8"))

    assert (run_folder / "generated.png").exists()
    assert manifest["operation"] == "generate"
    assert manifest["paid"] is True
    assert manifest["dna_subject"] == "outside"
    assert manifest["dna_version"] == "2.7"
    assert manifest["reference_mode"] == "environment"
    assert manifest["required_entities"]
    assert manifest["artifacts"][0]["sha256"]

    with pytest.raises(FileExistsError):
        RunStore(data_root=tmp_path).create_run("pkg-p3-001", manifest["run_id"], b"again", manifest)


def test_paid_policy_allows_one_generate_one_repair_then_needs_review(tmp_path: Path) -> None:
    generate_folder = generate_image_run(_prompt_contract(), content_package_id="pkg-p3-002", data_root=tmp_path, paid=True)
    original = json.loads((generate_folder / "manifest.json").read_text(encoding="utf-8"))
    existing = [
        ImageRun(
            run_id=original["run_id"],
            content_package_id="pkg-p3-002",
            creative_brief_id=original["creative_brief_id"],
            operation="generate",
            paid=True,
            state="NEEDS_REVIEW",
        )
    ]

    repair_folder = repair_image_run(original, issue="restore the rooftop railing", data_root=tmp_path, existing_runs=existing)
    repaired = json.loads((repair_folder / "manifest.json").read_text(encoding="utf-8"))

    assert repaired["operation"] == "edit"
    assert repaired["repair_of_run_id"] == original["run_id"]
    assert repaired["attempt_index"] == 2

    existing.append(
        ImageRun(
            run_id=repaired["run_id"],
            content_package_id="pkg-p3-002",
            creative_brief_id=repaired["creative_brief_id"],
            operation="repair",
            paid=True,
            state="NEEDS_REVIEW",
        )
    )
    with pytest.raises(ValueError, match="one targeted repair"):
        repair_image_run(original, issue="try another variant", data_root=tmp_path, existing_runs=existing)


def test_transient_provider_error_does_not_create_variant(tmp_path: Path) -> None:
    provider = MockImageProvider(fail_with_status=429)

    with pytest.raises(RuntimeError, match="backoff without creating"):
        generate_image_run(_prompt_contract(), content_package_id="pkg-p3-003", data_root=tmp_path, provider=provider, paid=True)

    assert provider.calls == 1
    assert RunStore(data_root=tmp_path).list_runs("pkg-p3-003") == []


def test_alignment_and_derivative_qc_exit_gate() -> None:
    brief = {"visual": {"required_entities": ["west_lake", "rooftop_railing"], "forbidden_entities": ["bedroom_window"]}}
    aligned = validate_alignment(brief, {"entities": ["west_lake"]}, {"entities": ["rooftop_railing"]})
    derivatives = validate_derivatives([{"path": "generated.png", "crop_safe": True, "ocr_pass": True}])

    assert aligned["alignment_score"] == 1.0
    assert aggregate_image_verdict(aligned, derivatives) == "APPROVED"

    missing = validate_alignment(brief, {"entities": ["west_lake"]}, {})
    assert missing["missing_required_entities"] == ["rooftop_railing"]
    assert "missing_required_subject" in missing["kill_switches"]
    assert aggregate_image_verdict(missing, derivatives) == "NEEDS_REVIEW"

    bad_crop = validate_derivatives([{"path": "story.png", "crop_safe": False}])
    assert "crop_safety_failed" in bad_crop["kill_switches"]
