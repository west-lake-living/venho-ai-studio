from pathlib import Path

import pytest
from PIL import Image

from image_studio_runtime.action_composite.masks import hierarchical_face_masks, geometry_preserving_identity_mask
from image_studio_runtime.action_composite.models import ActionCompositeJob, BoundingBox
from image_studio_runtime.action_composite.pipeline import ActionCompositePipeline
from image_studio_runtime.action_composite.workflow_v2 import CandidateSelector, RegionalGate, SceneCandidate


def test_candidate_selection_does_not_use_face_score() -> None:
    candidates = [
        SceneCandidate(candidate_id="a", image_path="a.png", scores={"pose": 96, "anatomy": 95, "outfit": 94, "environment": 94, "face": 20}),
        SceneCandidate(candidate_id="b", image_path="b.png", scores={"pose": 80, "anatomy": 80, "outfit": 80, "environment": 80, "face": 100}),
    ]
    assert CandidateSelector().select(candidates).candidate_id == "a"


def test_regional_gate_fails_closed_until_all_regions_are_validated() -> None:
    gate = RegionalGate(identity=93, eyes_brows=91, geometry=94, anatomy=95,
                        outfit=95, environment=95, global_composite=94,
                        pixel_preservation=True)
    assert gate.evaluate() == (True, [])
    gate.identity = None
    approved, failures = gate.evaluate()
    assert not approved
    assert "identity_unvalidated" in failures


def test_hierarchical_masks_have_expected_regions() -> None:
    masks = hierarchical_face_masks((200, 200), BoundingBox(left=70, top=50, right=130, bottom=120))
    assert masks.version == "hierarchical_face_v1"
    assert masks.core.size == masks.shape.size == masks.boundary.size == (200, 200)
    assert masks.core.getpixel((100, 80)) > 0
    assert masks.boundary.getpixel((20, 20)) == 0


def test_geometry_preserving_mask_uses_landmarks_and_never_touches_crop_boundary() -> None:
    mask, metadata = geometry_preserving_identity_mask(
        (220, 180), BoundingBox(left=70, top=40, right=150, bottom=140),
        [(90, 75), (130, 75), (110, 98), (96, 118), (124, 118)], feather=4,
    )
    assert mask.getbbox() is not None
    assert metadata["source"] == "InsightFace buffalo_l five-point landmarks"
    assert metadata["touches_crop_boundary"] is False
    assert metadata["coverage_ratio"] > 0


def test_geometry_preserving_mask_requires_five_landmarks() -> None:
    with pytest.raises(ValueError, match="five"):
        geometry_preserving_identity_mask(
            (220, 180), BoundingBox(left=70, top=40, right=150, bottom=140),
            [(90, 75)],
        )


def test_a2_hash_is_locked_in_manifest(tmp_path: Path) -> None:
    base = tmp_path / "candidate.png"
    reference = tmp_path / "A2-front.png"
    Image.new("RGBA", (160, 160), (20, 30, 40, 255)).save(base)
    reference.write_bytes(b"authoritative-a2")
    expected = __import__("hashlib").sha256(reference.read_bytes()).hexdigest()
    job = ActionCompositeJob(job_id="hash-lock", base_image=str(base), identity_reference=str(reference),
                             identity_reference_sha256=expected,
                             face_bbox={"left": 55, "top": 35, "right": 105, "bottom": 95})

    class Restorer:
        def restore(self, base_image, identity_reference, face_mask, geometry, config):
            return base_image.copy()

    result = ActionCompositePipeline().run(job, Restorer(), output_dir=tmp_path / "run")
    manifest = __import__("json").loads((tmp_path / "run" / "manifest.json").read_text())
    assert manifest["identity_authority"]["name"] == "A2-FRONT"
    assert manifest["identity_authority"]["sha256"] == expected


def test_a2_hash_mismatch_is_rejected(tmp_path: Path) -> None:
    base = tmp_path / "candidate.png"
    reference = tmp_path / "A2-front.png"
    Image.new("RGBA", (160, 160), "white").save(base)
    reference.write_bytes(b"authoritative-a2")
    job = ActionCompositeJob(job_id="hash-mismatch", base_image=str(base), identity_reference=str(reference),
                             identity_reference_sha256="0" * 64,
                             face_bbox={"left": 55, "top": 35, "right": 105, "bottom": 95})
    with pytest.raises(ValueError, match="hash"):
        ActionCompositePipeline().run(job, lambda: None, output_dir=tmp_path / "run")
