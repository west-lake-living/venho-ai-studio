from pathlib import Path

import pytest
from pydantic import ValidationError

from image_studio_runtime.action_composite.regional_score_gateway import (
    REGIONAL_FIELDS,
    RegionalScoreBlocked,
    RegionalScoreEvidence,
    RegionalScoreGateway,
    ValidatorStudioScoreProducer,
    GeometryEvidenceProducer,
    SceneEvidenceProducer,
)
from image_studio_runtime.action_composite.models import BoundingBox, FaceGeometry
from image_studio_runtime.action_composite.workflow_v2 import SceneCandidate
from image_studio_runtime.action_composite.workflow_v2 import RegionalGate


def _face_report():
    from validator_studio.schemas.validation_base import ArtifactRef, ValidationReport
    return ValidationReport(
        project="venho_hotel", subject="linh_an", validation_type="face",
        artifact_ref=ArtifactRef(type="face", file="face.png", hash="0" * 64),
        overall_score=94, dna_match_score=93,
        category_scores={"eyes_and_brows": 92},
    )


def _image_report():
    from validator_studio.schemas.validation_base import ArtifactRef, ValidationReport
    return ValidationReport(
        project="venho_hotel", subject="lake_view_room", validation_type="image",
        artifact_ref=ArtifactRef(type="image", file="image.png", hash="1" * 64),
        overall_score=91, dna_match_score=91,
    )


def test_gateway_produces_all_fields_from_explicit_sources():
    evidence = RegionalScoreEvidence(
        face_report=_face_report(), image_report=_image_report(), geometry_score=94,
        anatomy_score=95, outfit_score=96, environment_score=97,
        geometry_source_artifacts=["geometry.json"], scene_source_artifacts=["candidate.json"],
    )
    result = RegionalScoreGateway().build(evidence)
    assert set(result.scores) == set(REGIONAL_FIELDS)
    assert result.sources["identity"].endswith("face_report.dna_match_score")
    assert result.sources["anatomy"] == "scene candidate/anatomy producer"


def test_gateway_never_defaults_missing_evidence():
    evidence = RegionalScoreEvidence(face_report=_face_report())
    with pytest.raises(RegionalScoreBlocked, match="missing evidence"):
        RegionalScoreGateway().build(evidence)


def test_gateway_rejects_missing_face_subscore():
    from validator_studio.schemas.validation_base import ArtifactRef, ValidationReport
    face = ValidationReport(project="p", subject="s", validation_type="face",
                            artifact_ref=ArtifactRef(type="face", file="face.png", hash="0" * 64),
                            dna_match_score=90)
    evidence = RegionalScoreEvidence(face_report=face)
    with pytest.raises(RegionalScoreBlocked, match="eyes_and_brows"):
        RegionalScoreGateway().build(evidence)


def test_existing_gate_thresholds_are_unchanged():
    gate = RegionalGate()
    assert gate.thresholds == {"identity": 90.0, "eyes_brows": 90.0, "geometry": 92.0,
                               "anatomy": 90.0, "outfit": 90.0, "environment": 90.0,
                               "global_composite": 90.0}


def test_validator_studio_producer_requires_a_real_provider():
    with pytest.raises(RegionalScoreBlocked, match="provider"):
        ValidatorStudioScoreProducer().produce(
            project="p", subject="s", restored_path="restored.png",
            identity_reference_path="A2-front.png", image_subject="scene",
            provider="", geometry_score=94, anatomy_score=95, outfit_score=96,
            environment_score=97,
        )


def test_validator_studio_producer_rejects_mock_evidence():
    with pytest.raises(RegionalScoreBlocked, match="mock"):
        ValidatorStudioScoreProducer().produce(
            project="p", subject="s", restored_path="restored.png",
            identity_reference_path="A2-front.png", image_subject="scene",
            provider="mock", geometry_score=94, anatomy_score=95, outfit_score=96,
            environment_score=97,
        )


def test_geometry_producer_is_numeric_and_not_a_boolean_lock_conversion():
    geometry = FaceGeometry(
        face_bbox=BoundingBox(left=10, top=10, right=50, bottom=60),
        head_bbox=BoundingBox(left=0, top=0, right=70, bottom=80), face_scale=0.4,
    )
    score, producer, provenance = GeometryEvidenceProducer().produce(
        geometry, geometry, source_artifacts=["base.png", "restored.png"]
    )
    assert score == 100.0
    assert producer == "GeometryEvidenceProducer.geometry-evidence-v1"
    assert provenance["raw_evidence"]["bbox_iou"] == 1.0
    assert provenance["resulting_score"] == score


def test_scene_producer_rejects_malformed_numeric_evidence():
    with pytest.raises((RegionalScoreBlocked, ValueError)):
        candidate = SceneCandidate(candidate_id="scene-1", image_path="scene.png",
                                   scores={"anatomy": "excellent"})
        SceneEvidenceProducer().produce(candidate, source_artifacts=["scene.json"])


def test_replay_does_not_touch_comfyui_and_persists_only_qc_metadata(tmp_path: Path):
    root = tmp_path / "run"
    (root / "composite").mkdir(parents=True)
    (root / "composite" / "manifest.json").write_text("{}", encoding="utf-8")
    result = RegionalScoreGateway().replay(
        root, evidence=RegionalScoreEvidence(face_report=_face_report(), image_report=_image_report(),
                                              geometry_score=94, anatomy_score=95, outfit_score=96,
                                              environment_score=97,
                                              geometry_source_artifacts=["geometry.json"],
                                              scene_source_artifacts=["candidate.json"]))
    assert set(result.scores) == set(REGIONAL_FIELDS)
    assert (root / "regional_scores.json").is_file()
