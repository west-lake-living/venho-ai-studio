from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from image_studio_runtime.action_composite.masks import crop_for_identity
from image_studio_runtime.action_composite.models import ActionCompositeJob, BoundingBox
from image_studio_runtime.action_composite.pipeline import ActionCompositePipeline
from image_studio_runtime.action_composite.locks import GeometryLock
from image_studio_runtime.action_composite.models import FaceGeometry


class FakeRestorer:
    def restore(self, base_image, identity_reference, face_mask, geometry, config):
        output = base_image.copy()
        draw = ImageDraw.Draw(output)
        bbox = geometry["face_bbox"]
        draw.ellipse((bbox["left"], bbox["top"], bbox["right"], bbox["bottom"]), fill=(220, 160, 140, 255))
        return output


class BackgroundMutatingRestorer(FakeRestorer):
    """Repaints a corner far outside the face mask, leaving alpha untouched."""

    def restore(self, base_image, identity_reference, face_mask, geometry, config):
        output = super().restore(base_image, identity_reference, face_mask, geometry, config)
        output.putpixel((0, 0), (255, 0, 0, 255))
        return output


def _make_job(tmp_path: Path) -> ActionCompositeJob:
    base_path = tmp_path / "candidate.png"
    reference_path = tmp_path / "A2-front.png"
    Image.new("RGBA", (160, 160), (20, 30, 40, 255)).save(base_path)
    Image.new("RGBA", (64, 64), (200, 150, 130, 255)).save(reference_path)
    return ActionCompositeJob(job_id="linhan_action_0001", base_image=str(base_path),
                              identity_reference=str(reference_path),
                              face_bbox=BoundingBox(left=55, top=35, right=105, bottom=95))


def test_action_composite_restores_face_and_preserves_locked_pixels(tmp_path: Path) -> None:
    job = _make_job(tmp_path)
    result = ActionCompositePipeline().run(job, FakeRestorer(), output_dir=tmp_path / "run", identity_score=91.2, geometry_score=93.0)
    assert result.qc.status == "PASS"
    assert result.qc.pixel_preservation is True
    assert (tmp_path / "run" / "image.png").exists()
    assert (tmp_path / "run" / "manifest.json").exists()


def test_rgb_only_mutation_outside_mask_is_caught(tmp_path: Path) -> None:
    """An alpha-only diff would call this run clean: body, wardrobe and the West
    Lake background can all change without touching the alpha channel."""
    job = _make_job(tmp_path)
    result = ActionCompositePipeline().run(job, BackgroundMutatingRestorer(), output_dir=tmp_path / "run",
                                           identity_score=95.0, geometry_score=93.0)
    assert result.qc.pixel_preservation is False
    assert "pixel_preservation_failed" in result.qc.failures
    assert result.qc.status == "FAIL"


def test_failed_gate_without_identity_score_is_fail_not_unvalidated(tmp_path: Path) -> None:
    job = _make_job(tmp_path)
    result = ActionCompositePipeline().run(job, BackgroundMutatingRestorer(), output_dir=tmp_path / "run")
    assert result.qc.status == "FAIL"


def test_zero_identity_score_is_a_hard_failure(tmp_path: Path) -> None:
    job = _make_job(tmp_path)
    result = ActionCompositePipeline().run(job, FakeRestorer(), output_dir=tmp_path / "run", identity_score=0.0)
    assert result.qc.status == "FAIL"
    assert "identity_below_threshold" in result.qc.failures


def test_unscored_but_clean_run_is_unvalidated(tmp_path: Path) -> None:
    job = _make_job(tmp_path)
    result = ActionCompositePipeline().run(job, FakeRestorer(), output_dir=tmp_path / "run")
    assert result.qc.status == "UNVALIDATED"


def test_only_a2_front_is_allowed() -> None:
    with pytest.raises(ValueError, match="A2-FRONT"):
        ActionCompositeJob(job_id="bad", base_image="x", identity_reference="candidate-93.png")


def test_a2_in_a_folder_name_is_not_the_identity_authority() -> None:
    with pytest.raises(ValueError, match="A2-FRONT"):
        ActionCompositeJob(job_id="bad", base_image="x",
                           identity_reference="data/A2_benchmarks/candidate-93.png")


def test_crop_scale_below_one_is_rejected() -> None:
    image = Image.new("RGBA", (160, 160))
    with pytest.raises(ValueError, match="crop scale"):
        crop_for_identity(image, BoundingBox(left=55, top=35, right=105, bottom=95), scale=0.5)


def test_geometry_lock_rejects_head_pose_mutation() -> None:
    geometry = FaceGeometry(face_bbox=BoundingBox(left=55, top=35, right=105, bottom=95),
                            head_bbox=BoundingBox(left=40, top=2, right=120, bottom=128), face_scale=0.31)
    candidate = geometry.model_copy(update={"yaw": 12.0})
    valid, failures = GeometryLock(geometry).validate(candidate)
    assert valid is False
    assert failures == ["yaw_changed"]
