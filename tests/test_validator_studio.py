from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from validator_studio.content_validator import validate_content
from knowledge_studio.vision.cli import app
from validator_studio.face_validator import validate_face
from validator_studio.image_validator import validate_image
from validator_studio.observe_adapter import ObservationSchemaError, observe_image_against_dna
from validator_studio.prompt_resolver import resolve_latest_prompt_path
from validator_studio.prompt_validator import validate_prompt, validate_prompt_contract
from validator_studio.report_builder import write_report
from validator_studio.schemas.face_validation import FaceGateResult, FaceValidationObservation
from validator_studio.schemas.image_validation import DnaMatchObservation, ForbiddenObservation, ImageObservation
from validator_studio.schemas.validation_base import MatchState, Severity
from validator_studio.scoring import CONTENT_CATEGORIES, IMAGE_CATEGORIES, PROMPT_CATEGORIES, score_face_observation, score_image_observation, validate_weights
from validator_studio.utils import validation_config


def test_validation_weights_are_exact_categories_and_total_one():
    config = validation_config()
    validate_weights(config["image_validation_weights"], IMAGE_CATEGORIES)
    validate_weights(config["prompt_validation_weights"], PROMPT_CATEGORIES)
    validate_weights(config["content_validation_weights"], CONTENT_CATEGORIES)


def test_same_observation_produces_same_score():
    config = validation_config()
    observation = ImageObservation(
        dna_matches=[
            DnaMatchObservation(key="window_frame", expected="black aluminum", observed="black aluminum", match_state=MatchState.MATCH),
            DnaMatchObservation(key="floor", expected="hardwood", observed="marble", match_state=MatchState.MISMATCH),
        ],
        forbidden=[],
    )
    first = score_image_observation(observation, config)
    second = score_image_observation(observation, config)
    assert first.overall_score == second.overall_score
    assert first.category_scores == second.category_scores


def test_high_forbidden_triggers_kill_switch_cap():
    config = validation_config()
    observation = ImageObservation(
        dna_matches=[
            DnaMatchObservation(key="window_frame", expected="black aluminum", observed="black aluminum", match_state=MatchState.MATCH),
        ],
        forbidden=[
            ForbiddenObservation(rule="no floor-to-ceiling glass wall", severity=Severity.HIGH, violated=True)
        ],
    )
    result = score_image_observation(observation, config)
    assert result.kill_switch.triggered is True
    assert result.overall_score <= config["kill_switch"]["forbidden_high_cap"]
    assert result.verdict.value == "reject"
    assert result.recommendation.value == "regenerate"


def test_image_validator_mock_writes_report(tmp_path):
    image = tmp_path / "good.png"
    image.write_bytes(b"fake-image-bytes")
    report = validate_image("venho_hotel", "lake_view_room", image, provider="mock")
    paths = write_report(report, tmp_path / "reports", "sample")
    md = paths["md"].read_text(encoding="utf-8")
    data = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert "# VALIDATION REPORT" in md
    assert "## OVERALL SCORE" in md
    assert data["module"] == "validator_studio"
    assert data["validation_type"] == "image"


def test_image_observe_provider_path_includes_dna_and_rejects_ai_score(tmp_path, monkeypatch):
    image = tmp_path / "generated.png"
    image.write_bytes(b"fake-image")
    calls = {}

    class FakeClient:
        def __init__(self, image_provider="openai", temperature=0.0):
            calls["provider"] = image_provider
            calls["temperature"] = temperature

        def analyze_image(self, image_path, system_prompt):
            calls["prompt"] = system_prompt
            return {
                "dna_matches": [
                    {
                        "key": "window_frame",
                        "expected": "matte black aluminum window frame",
                        "observed": "matte black aluminum window frame",
                        "category": "dna_match",
                        "match_state": "match",
                        "confidence": 1.0,
                        "reason": "visible",
                    }
                ],
                "forbidden": [],
                "allowed_imperfections": [],
                "notes": [],
            }

    monkeypatch.setattr("validator_studio.observe_adapter.VisionClient", FakeClient)
    observation = observe_image_against_dna(
        image,
        {"invariant": [{"key": "window_frame", "value": "matte black aluminum window frame"}]},
        provider="openai",
    )
    assert calls["provider"] == "openai"
    assert calls["temperature"] == 0.0
    assert "VALIDATION INPUT JSON" in calls["prompt"]
    assert "matte black aluminum window frame" in calls["prompt"]
    assert observation.dna_matches[0].match_state.value == "match"


def test_image_observe_provider_rejects_scoring_fields(tmp_path, monkeypatch):
    image = tmp_path / "generated.png"
    image.write_bytes(b"fake-image")

    class FakeClient:
        def __init__(self, image_provider="openai", temperature=0.0):
            pass

        def analyze_image(self, image_path, system_prompt):
            return {
                "overall_score": 99,
                "dna_matches": [],
                "forbidden": [],
                "allowed_imperfections": [],
            }

    monkeypatch.setattr("validator_studio.observe_adapter.VisionClient", FakeClient)
    try:
        observe_image_against_dna(image, {"invariant": []}, provider="openai")
    except ObservationSchemaError as exc:
        assert "overall_score" in str(exc)
    else:
        raise AssertionError("expected ObservationSchemaError")


def test_prompt_validator_reads_prompt_json(tmp_path):
    prompt_file = tmp_path / "prompt.json"
    prompt_file.write_text(json.dumps({
        "project": "venho_hotel",
        "prompt_type": "image",
        "prompt_version": "1.0",
        "required_dna": [
            {"key": "window_frame", "value": "matte black aluminum window frame"},
            {"key": "bed_size", "value": "double bed"},
        ],
        "forbidden": [{"rule": "no floor-to-ceiling glass wall", "source": "curated"}],
        "final_prompt": "Realistic hotel room photo with matte black aluminum window frame and double bed.",
    }), encoding="utf-8")
    report = validate_prompt("venho_hotel", "lake_view_room", prompt_file)
    assert report.validation_type == "prompt"
    assert report.category_scores["dna_coverage"] > 50
    assert "Module 02" in report.validation_notes[0]


def test_prompt_validator_scores_in_memory_contract_for_module_02():
    contract = {
        "project": "venho_hotel",
        "prompt_type": "image",
        "prompt_version": "1.0",
        "required_dna": [
            {"key": "window_frame", "value": "matte black aluminum window frame"},
            {"key": "bed_size", "value": "double bed"},
        ],
        "forbidden": [{"rule": "no floor-to-ceiling glass wall", "source": "curated"}],
        "final_prompt": "Realistic hotel room photo with matte black aluminum window frame and double bed.",
    }
    report = validate_prompt_contract("venho_hotel", "lake_view_room", contract)
    assert report.artifact_ref.file == "(in-memory prompt contract)"
    assert report.validation_type == "prompt"
    assert report.category_scores["dna_coverage"] > 50


def test_prompt_resolver_finds_active_manifest_prompt():
    path = resolve_latest_prompt_path("venho_hotel", "lake_view_room", "image", "booking-style")
    assert path.name == "LAKE_VIEW_ROOM__booking-style__IMAGE_PROMPT_v1.0.json"
    assert path.exists()


def test_cli_validate_prompt_command(tmp_path):
    prompt_file = tmp_path / "prompt.json"
    prompt_file.write_text(json.dumps({
        "project": "venho_hotel",
        "prompt_type": "image",
        "prompt_version": "1.0",
        "required_dna": [{"key": "window_frame", "value": "matte black aluminum window frame"}],
        "final_prompt": "Realistic photo with matte black aluminum window frame.",
    }), encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(app, [
        "validate", "prompt",
        "--project", "venho_hotel",
        "--subject", "lake_view_room",
        "--prompt-file", str(prompt_file),
    ])
    assert result.exit_code == 0
    assert "Validation complete." in result.output


def test_cli_validate_prompt_latest_from_manifest():
    runner = CliRunner()
    result = runner.invoke(app, [
        "validate", "prompt",
        "--project", "venho_hotel",
        "--subject", "lake_view_room",
        "--latest",
        "--type", "image",
        "--brief-slug", "booking-style",
    ])
    assert result.exit_code == 0
    assert "Validation complete." in result.output


def test_face_validator_passes_binary_gates_before_weighted_score(tmp_path):
    image = tmp_path / "linh_an_good.png"
    image.write_bytes(b"fake-face-image")
    report = validate_face("venho_hotel", "linh_an", image, provider="mock")
    assert report.validation_type == "face"
    assert report.kill_switch.triggered is False
    assert report.overall_score > 0
    assert all(score.status.value == "ok" for score in report.section_scores if score.section == "face_gate")
    assert "grounding/web search disabled" in report.validation_notes[1]


def test_face_validator_failed_gate_overrides_weighted_score(tmp_path):
    image = tmp_path / "linh_an_fail.png"
    image.write_bytes(b"fake-face-image")
    report = validate_face("venho_hotel", "linh_an", image, provider="mock")
    assert report.kill_switch.triggered is True
    assert report.kill_switch.reason == "face binary gate failed"
    assert report.overall_score == 0
    assert report.verdict.value == "reject"
    assert report.issues[0].severity.value == "high"


def test_face_validator_provider_path_uses_rubric_and_schema_guard(tmp_path, monkeypatch):
    image = tmp_path / "linh_an_provider.png"
    image.write_bytes(b"fake-face-image")
    calls = {}

    class FakeClient:
        def __init__(self, image_provider="openai", temperature=0.0):
            calls["provider"] = image_provider
            calls["temperature"] = temperature

        def analyze_image(self, image_path, system_prompt):
            calls["prompt"] = system_prompt
            return {
                "gates": [
                    {"gate": "identity_structure", "passed": True, "reason": "ok", "evidence": "fictional DNA only"},
                    {"gate": "eye_ratio", "passed": True, "reason": "ok", "evidence": "fictional DNA only"},
                    {"gate": "forbidden_traits", "passed": True, "reason": "ok", "evidence": "fictional DNA only"},
                ],
                "weighted_scores": {
                    "facial_shape": 90,
                    "eyes": 88,
                    "hair": 87,
                    "expression": 86,
                    "technical_quality": 85,
                },
                "notes": [],
            }

    monkeypatch.setattr("validator_studio.face_validator.VisionClient", FakeClient)
    report = validate_face("venho_hotel", "linh_an", image, provider="openai")
    assert calls["provider"] == "openai"
    assert calls["temperature"] == 0.0
    assert "rubric_07f" in calls["prompt"]
    assert "no real-person identification" in calls["prompt"]
    assert report.kill_switch.triggered is False
    assert report.overall_score > 0


def test_face_scoring_normalizes_observer_scores_from_zero_to_one():
    observation = FaceValidationObservation(
        gates=[FaceGateResult(gate="identity_structure", passed=True)],
        weighted_scores={
            "facial_shape": 0.30,
            "eyes": 0.25,
            "hair": 0.20,
            "expression": 0.15,
            "technical_quality": 0.10,
        },
    )
    rubric = {
        "weighted": {
            "facial_shape": 0.30,
            "eyes": 0.25,
            "hair": 0.20,
            "expression": 0.15,
            "technical_quality": 0.10,
        }
    }

    result = score_face_observation(observation, rubric)

    assert result.category_scores["facial_shape"] == 30
    assert result.category_scores["technical_quality"] == 10
    assert result.overall_score == 22.5


def test_face_validator_provider_rejects_identity_matching_fields(tmp_path, monkeypatch):
    image = tmp_path / "linh_an_provider.png"
    image.write_bytes(b"fake-face-image")

    class FakeClient:
        def __init__(self, image_provider="openai", temperature=0.0):
            pass

        def analyze_image(self, image_path, system_prompt):
            return {"identity_match": "celebrity", "gates": [], "weighted_scores": {}}

    monkeypatch.setattr("validator_studio.face_validator.VisionClient", FakeClient)
    try:
        validate_face("venho_hotel", "linh_an", image, provider="openai")
    except ObservationSchemaError as exc:
        assert "identity_match" in str(exc)
    else:
        raise AssertionError("expected ObservationSchemaError")


def test_cli_validate_face_command(tmp_path):
    image = tmp_path / "linh_an_good.png"
    image.write_bytes(b"fake-face-image")
    runner = CliRunner()
    result = runner.invoke(app, [
        "validate", "face",
        "--project", "venho_hotel",
        "--subject", "linh_an",
        "--image", str(image),
    ])
    assert result.exit_code == 0
    assert "Validation complete." in result.output


def test_content_validator_scores_good_vietnamese_draft(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text(
        "Một buổi chiều bên Hồ Tây luôn có nhịp rất riêng: mặt nước dịu, phố Nguyễn Đình Thi "
        "chậm lại, và Ven Ho Hotel là điểm dừng chân ấm áp cho những ai muốn ở gần đời sống "
        "địa phương thật của Hà Nội. Nếu bạn cần một nơi nghỉ boutique mid-range, yên tĩnh và "
        "thuận tiện, hãy nhắn trang để kiểm tra phòng còn trống.",
        encoding="utf-8",
    )
    report = validate_content("venho_hotel", "westlake", draft, target_language="vi")
    assert report.validation_type == "content"
    assert report.category_scores["language_fit"] == 100
    assert report.category_scores["cta"] == 100
    assert report.overall_score >= 70


def test_content_validator_flags_restriction_and_missing_language_fit(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text(
        "Ven Ho Hotel is the best in Hanoi, a 5 star luxury resort. BOOK NOW!!!",
        encoding="utf-8",
    )
    report = validate_content("venho_hotel", "westlake", draft, target_language="vi")
    assert report.category_scores["language_fit"] < 80
    assert report.category_scores["tone"] < 70
    assert any(issue.severity.value == "high" for issue in report.issues)


def test_cli_validate_content_command(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text(
        "Một góc Hồ Tây chậm rãi, gần gũi và thật đời thường. Ven Ho Hotel là điểm dừng chân "
        "ấm áp để bạn bắt đầu buổi sáng bên hồ. Nhắn trang để kiểm tra phòng còn trống.",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(app, [
        "validate", "content",
        "--project", "venho_hotel",
        "--subject", "westlake",
        "--draft-file", str(draft),
        "--lang", "vi",
    ])
    assert result.exit_code == 0
    assert "Validation complete." in result.output
