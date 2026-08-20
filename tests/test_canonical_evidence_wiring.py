import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from image_studio_runtime.action_composite.geometry import (FaceGeometryEvidenceBlocked,
                                                             FullFrameReinsertionGeometryRecovery,
                                                             InsightFaceGeometryExtractor)
from image_studio_runtime.action_composite.models import ActionCompositeJob, BoundingBox, FaceGeometry
from image_studio_runtime.action_composite.pipeline import ActionCompositePipeline
from image_studio_runtime.action_composite.regional_score_gateway import ValidatorExecutionContext
from image_studio_runtime.action_composite.workflow_v2 import SceneCandidate


class Restorer:
    def restore(self, base, identity_reference, face_mask, geometry, config):
        output = base.copy()
        output.putpixel((geometry["face_bbox"]["left"], geometry["face_bbox"]["top"]), (220, 160, 140, 255))
        return output


def _job(tmp_path: Path) -> ActionCompositeJob:
    base = tmp_path / "base.png"
    reference = tmp_path / "A2-front.png"
    Image.new("RGBA", (160, 160), "white").save(base)
    Image.new("RGBA", (64, 64), "gray").save(reference)
    return ActionCompositeJob(
        job_id="canonical-wiring", base_image=str(base), identity_reference=str(reference),
        face_bbox=BoundingBox(left=55, top=35, right=105, bottom=95),
    )


def _geometry() -> FaceGeometry:
    return FaceGeometry(
        face_bbox=BoundingBox(left=55, top=35, right=105, bottom=95),
        head_bbox=BoundingBox(left=27, top=2, right=133, bottom=128), face_scale=0.3125,
    )


class _ObservedGeometryExtractor:
    last_provenance = {
        "original_dimensions": {"width": 160, "height": 160},
        "analysis_dimensions": {"width": 1024, "height": 1024},
        "scale_factor": 6.4,
        "preprocessing_method": "insightface-analysis-upscale-cubic-v1",
    }

    def __call__(self, _path: Path) -> FaceGeometry:
        return _geometry()


def test_actual_selected_candidate_and_observed_geometry_are_persisted(tmp_path: Path):
    job = _job(tmp_path)
    selected = SceneCandidate(
        candidate_id="selected-scene", image_path=job.base_image,
        scores={"pose": 96, "anatomy": 94, "outfit": 93, "environment": 92},
    )
    lower = SceneCandidate(
        candidate_id="other-scene", image_path=str(tmp_path / "other.png"),
        scores={"pose": 80, "anatomy": 80, "outfit": 80, "environment": 80},
    )
    output_dir = tmp_path / "run"
    ActionCompositePipeline().run(
        job, Restorer(), output_dir=output_dir,
        scene_candidates=[lower, selected], observed_geometry_extractor=_ObservedGeometryExtractor(),
        validator_context=ValidatorExecutionContext(provider="gemini", reference_artifacts=["A2-front.png"]),
    )
    manifest = json.loads((output_dir / "manifest.json").read_text())
    assert manifest["scene_candidate"]["candidate_id"] == "selected-scene"
    assert manifest["scene_candidate"]["scores"]["anatomy"] == 94
    assert manifest["face_geometry_evidence"]["observed"]["extraction_method"] == "face-geometry-extractor-v1"
    assert manifest["face_geometry_evidence"]["observed"]["provenance"]["scale_factor"] == 6.4
    assert manifest["validator_context"]["provider"] == "gemini"
    assert Path(manifest["face_geometry_evidence"]["observed"]["source_artifact"]).is_file()


def test_candidate_from_another_source_is_blocked(tmp_path: Path):
    job = _job(tmp_path)
    candidate = SceneCandidate(candidate_id="wrong", image_path=str(tmp_path / "other.png"),
                               scores={"anatomy": 95, "outfit": 95, "environment": 95})
    with pytest.raises(ValueError, match="source must equal"):
        ActionCompositePipeline().run(job, Restorer(), output_dir=tmp_path / "run",
                                      selected_candidate=candidate)


def test_observed_geometry_requires_an_extractor_for_capture(tmp_path: Path):
    job = _job(tmp_path)
    output_dir = tmp_path / "run"
    ActionCompositePipeline().run(job, Restorer(), output_dir=output_dir)
    manifest = json.loads((output_dir / "manifest.json").read_text())
    assert manifest["face_geometry_evidence"] is None


class _SingleFaceAnalyzer:
    def get(self, _image):
        return [SimpleNamespace(
            bbox=[50, 30, 110, 100],
            kps=[[65, 55], [95, 55], [80, 70], [68, 88], [92, 88]],
            det_score=0.95,
        )]


class _NoFaceAnalyzer:
    def get(self, _image):
        return []


class _MultipleFaceAnalyzer:
    def get(self, _image):
        return [_SingleFaceAnalyzer().get(_image)[0], _SingleFaceAnalyzer().get(_image)[0]]


class _PnP:
    SOLVEPNP_ITERATIVE = 0
    SOLVEPNP_SQPNP = 1
    INTER_CUBIC = 2

    @staticmethod
    def resize(image, size, interpolation):
        import numpy as np
        assert interpolation == _PnP.INTER_CUBIC
        height, width = size[1], size[0]
        return np.zeros((height, width, image.shape[2]), dtype=image.dtype)

    @staticmethod
    def solvePnP(*_args, **_kwargs):
        return True, [[0.0], [0.0], [0.0]], [[0.0], [0.0], [1.0]]

    @staticmethod
    def projectPoints(object_points, *_args):
        import numpy as np
        return np.zeros((len(object_points), 1, 2), dtype=float), None

    @staticmethod
    def Rodrigues(_rotation):
        import numpy as np
        return np.eye(3), None


def test_insightface_extractor_uses_the_actual_artifact(tmp_path: Path):
    artifact = tmp_path / "final_composite.png"
    Image.new("RGB", (160, 160), "white").save(artifact)
    geometry = InsightFaceGeometryExtractor(analyzer=_SingleFaceAnalyzer(), cv2_module=_PnP()).extract(artifact)
    assert geometry.face_bbox == BoundingBox(left=8, top=5, right=17, bottom=16)
    assert geometry.face_scale == 9 / 160
    assert (geometry.yaw, geometry.pitch, geometry.roll) == (0.0, 0.0, 0.0)
    assert geometry.eye_line == pytest.approx(55 / 6.4)
    assert geometry.nose_axis == pytest.approx(80 / 6.4)
    assert InsightFaceGeometryExtractor.landmark_order == (
        "left_eye", "right_eye", "nose", "left_mouth_corner", "right_mouth_corner"
    )
    assert geometry is not None


def test_five_point_pnp_provenance_has_no_synthetic_landmark():
    provenance = InsightFaceGeometryExtractor(
        analyzer=_SingleFaceAnalyzer(), cv2_module=_PnP()
    )
    artifact = Path(__file__).with_name("_pnp-provenance-fixture.png")
    try:
        Image.new("RGB", (160, 160), "white").save(artifact)
        provenance.extract(artifact)
        pnp = provenance.last_provenance["pnp"]
        assert pnp["object_point_count"] == 5
        assert pnp["image_point_count"] == 5
        assert pnp["synthetic_landmarks_added"] == 0
    finally:
        artifact.unlink(missing_ok=True)


def test_invalid_landmark_count_fails_closed(tmp_path: Path):
    artifact = tmp_path / "invalid.png"
    Image.new("RGB", (160, 160), "white").save(artifact)

    class FourPointAnalyzer:
        def get(self, _image):
            return [SimpleNamespace(bbox=[50, 30, 110, 100], kps=[[65, 55], [95, 55], [80, 70], [68, 88]])]

    with pytest.raises(FaceGeometryEvidenceBlocked, match="lacks one face bbox or five landmarks"):
        InsightFaceGeometryExtractor(analyzer=FourPointAnalyzer(), cv2_module=_PnP()).extract(artifact)


def test_insightface_extractor_blocks_when_no_observed_face_exists(tmp_path: Path):
    artifact = tmp_path / "final_composite.png"
    Image.new("RGB", (160, 160), "white").save(artifact)
    with pytest.raises(FaceGeometryEvidenceBlocked, match="exactly one face"):
        InsightFaceGeometryExtractor(analyzer=_NoFaceAnalyzer(), cv2_module=_PnP()).extract(artifact)


def test_insightface_extractor_upscales_in_memory_and_maps_coordinates(tmp_path: Path):
    artifact = tmp_path / "restored_crop.png"
    Image.new("RGB", (160, 80), "white").save(artifact)
    analyzer = _SingleFaceAnalyzer()
    extractor = InsightFaceGeometryExtractor(analyzer=analyzer, cv2_module=_PnP())
    geometry = extractor.extract(artifact)
    # The shortest side is scaled from 80 to 1024 (x12.8); detector coordinates
    # must be represented in the original artifact coordinate system.
    assert geometry.face_bbox == BoundingBox(left=4, top=2, right=9, bottom=8)
    assert geometry.face_scale == pytest.approx(5 / 160)
    assert extractor.last_provenance is not None
    assert extractor.last_provenance["original_artifact"] == str(artifact)
    assert len(extractor.last_provenance["original_sha256"]) == 64
    assert extractor.last_provenance["original_dimensions"] == {"width": 160, "height": 80}
    assert extractor.last_provenance["analysis_dimensions"] == {"width": 2048, "height": 1024}
    assert extractor.last_provenance["scale_factor"] == 12.8
    assert extractor.last_provenance["preprocessing_method"] == "insightface-analysis-upscale-cubic-v1"


@pytest.mark.parametrize("analyzer", [_NoFaceAnalyzer(), _MultipleFaceAnalyzer()])
def test_insightface_extractor_blocks_non_single_detection_after_preprocessing(tmp_path: Path, analyzer):
    artifact = tmp_path / "restored_crop.png"
    Image.new("RGB", (160, 80), "white").save(artifact)
    with pytest.raises(FaceGeometryEvidenceBlocked, match="exactly one face"):
        InsightFaceGeometryExtractor(analyzer=analyzer, cv2_module=_PnP()).extract(artifact)


class _RecordingSingleFaceAnalyzer(_SingleFaceAnalyzer):
    def __init__(self):
        self.input_shape = None

    def get(self, image):
        self.input_shape = image.shape
        return super().get(image)


def test_full_frame_reinsertion_persists_exact_placement_and_remaps_geometry(tmp_path: Path):
    base_path = tmp_path / "base.png"
    restored_path = tmp_path / "restored_crop.png"
    analysis_path = tmp_path / "analysis.png"
    Image.new("RGB", (160, 120), "white").save(base_path)
    Image.new("RGB", (80, 40), "black").save(restored_path)
    analyzer = _RecordingSingleFaceAnalyzer()
    recovery = FullFrameReinsertionGeometryRecovery(
        InsightFaceGeometryExtractor(analyzer=analyzer, cv2_module=_PnP())
    )
    result = recovery.recover(
        base_artifact=base_path, raw_restored_artifact=restored_path,
        crop_box=BoundingBox(left=20, top=10, right=120, bottom=110), analysis_artifact=analysis_path,
    )
    assert result.crop_box == BoundingBox(left=20, top=10, right=120, bottom=110)
    assert result.original_crop_size == (100, 100)
    assert result.raw_restored_size == (80, 40)
    assert result.detection_count == 1
    assert result.detection_score == 0.95
    assert analyzer.input_shape == (120, 160, 3)
    assert result.geometry.face_bbox == BoundingBox(left=30, top=20, right=90, bottom=90)
    assert result.geometry.face_scale == pytest.approx(0.6)
    assert result.landmarks_crop_relative[0] == (45.0, 45.0)


def test_full_frame_reinsertion_changes_only_the_recorded_crop(tmp_path: Path):
    base_path = tmp_path / "base.png"
    restored_path = tmp_path / "restored_crop.png"
    analysis_path = tmp_path / "analysis.png"
    Image.new("RGB", (160, 120), "white").save(base_path)
    Image.new("RGB", (80, 40), "black").save(restored_path)
    recovery = FullFrameReinsertionGeometryRecovery(
        InsightFaceGeometryExtractor(analyzer=_SingleFaceAnalyzer(), cv2_module=_PnP())
    )
    recovery.recover(base_artifact=base_path, raw_restored_artifact=restored_path,
                     crop_box=BoundingBox(left=20, top=10, right=120, bottom=110), analysis_artifact=analysis_path)
    import numpy as np
    base = np.asarray(Image.open(base_path).convert("RGB"))
    analysis = np.asarray(Image.open(analysis_path).convert("RGB"))
    changed = np.any(base != analysis, axis=2)
    assert not changed[:10, :].any()
    assert not changed[110:, :].any()
    assert not changed[:, :20].any()
    assert not changed[:, 120:].any()
    assert changed[10:110, 20:120].any()


def test_full_frame_reinsertion_blocks_without_crop_placement(tmp_path: Path):
    base_path = tmp_path / "base.png"
    restored_path = tmp_path / "restored_crop.png"
    Image.new("RGB", (160, 120), "white").save(base_path)
    Image.new("RGB", (80, 40), "black").save(restored_path)
    recovery = FullFrameReinsertionGeometryRecovery(
        InsightFaceGeometryExtractor(analyzer=_SingleFaceAnalyzer(), cv2_module=_PnP())
    )
    with pytest.raises(FaceGeometryEvidenceBlocked, match="Crop placement metadata"):
        recovery.recover(base_artifact=base_path, raw_restored_artifact=restored_path,
                         crop_box=None, analysis_artifact=tmp_path / "analysis.png")
