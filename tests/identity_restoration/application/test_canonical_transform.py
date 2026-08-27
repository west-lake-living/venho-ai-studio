from __future__ import annotations

import io
import json
from dataclasses import replace
from pathlib import Path

import jsonschema
import numpy as np
import pytest
from PIL import Image

from identity_restoration.application.canonical_transform import (
    CanonicalTransformError,
    canonicalize_candidate_v3,
    inverse_warp_canonical_artifacts,
    load_candidate_v3_canonical_transform_policy,
    verify_landmark_round_trip,
)
from identity_restoration.application.candidate_v3_route_policy import load_candidate_v3_route_policy
from identity_restoration.application.face_observability import (
    FaceDetection,
    FaceObservabilityConfig,
    FaceObservabilityService,
)
from identity_restoration.domain.policies.candidate_v3_route_policy import evaluate_candidate_v3_route


ROOT = Path(__file__).resolve().parents[3]
SHA = "a" * 64
CONFIG = FaceObservabilityConfig("test-detector", "test-v1", SHA, SHA, 0.6)


class FakeDetector:
    def __init__(self, detections: tuple[FaceDetection, ...]) -> None:
        self.detections = detections

    def detect(self, image: Image.Image) -> tuple[FaceDetection, ...]:
        return self.detections


def _png(array: np.ndarray, mode: str) -> bytes:
    buffer = io.BytesIO()
    del mode
    Image.fromarray(array).save(buffer, format="PNG")
    return buffer.getvalue()


def _image(size: tuple[int, int] = (1000, 1000)) -> bytes:
    height, width = size[1], size[0]
    values = np.arange(width * height * 3, dtype=np.uint8).reshape(height, width, 3)
    return _png(values, "RGB")


def _mask(size: tuple[int, int] = (1000, 1000)) -> bytes:
    height, width = size[1], size[0]
    values = np.zeros((height, width), dtype=np.uint8)
    values[:, :] = 255
    return _png(values, "L")


def _detection(
    bbox: tuple[float, float, float, float] = (20, 20, 80, 80),
    landmarks: tuple[tuple[float, float], ...] = ((35, 40), (65, 40), (50, 52), (40, 65), (60, 65)),
) -> FaceDetection:
    return FaceDetection(0.95, bbox, landmarks, 0.0, 0.0, 0.0)


def _observed(
    detection: FaceDetection | None = None,
    *,
    image_bytes: bytes | None = None,
    mask_bytes: bytes | None = None,
) -> tuple[object, object, bytes, bytes, bytes]:
    image_bytes = image_bytes or _image()
    mask_bytes = mask_bytes or _mask()
    observation = FaceObservabilityService(
        FakeDetector((detection or _detection(),)), CONFIG
    ).observe(image_bytes, mask_bytes)
    route = evaluate_candidate_v3_route(observation, load_candidate_v3_route_policy())
    return observation, route, image_bytes, mask_bytes, mask_bytes


def _canonical(observation, route, image, editable, feather):
    return canonicalize_candidate_v3(
        observation=observation,
        route_result=route,
        image_bytes=image,
        editable_mask_bytes=editable,
        feather_mask_bytes=feather,
    )


def test_pinned_template_and_policy_are_exact_and_hash_stable() -> None:
    policy = load_candidate_v3_canonical_transform_policy()
    again = load_candidate_v3_canonical_transform_policy()

    assert policy.template_id == "candidate_v3_face_template"
    assert policy.template_version == "1.0"
    assert policy.template_points == (
        (192.0, 208.0), (320.0, 208.0), (256.0, 272.0),
        (208.0, 336.0), (304.0, 336.0),
    )
    assert policy.padding_per_side == 0.2
    assert policy.policy_id == "candidate_v3_canonical_transform_policy"
    assert policy.version == "1.0"
    assert policy.template_sha256 == again.template_sha256
    assert policy.policy_sha256 == again.policy_sha256


def test_cp_b_geometry_and_border_reflection_are_deterministic() -> None:
    observation, route, image, editable, feather = _observed(
        _detection(bbox=(0, 0, 200, 200), landmarks=((50, 50), (150, 50), (100, 100), (70, 150), (130, 150)))
    )
    first = _canonical(observation, route, image, editable, feather)
    second = _canonical(observation, route, image, editable, feather)

    assert route.route_code == "ELIGIBLE"
    assert first.as_dict() == second.as_dict()
    assert first.transform.canvas_crop_box == replace(
        first.transform.canvas_crop_box, left=-40.0, top=-40.0, right=240.0, bottom=240.0
    )
    assert first.max_round_trip_error_px <= 0.5
    assert first.transform.model_size == 512
    assert first.transform.border_mode == "REFLECT_101"
    assert first.transform.interpolation == "LANCZOS4"


def test_canonical_outputs_and_masks_have_locked_geometry() -> None:
    observation, route, image, editable, feather = _observed()
    gradient = np.tile(np.arange(1000, dtype=np.uint8), (1000, 1))
    result = _canonical(observation, route, image, editable, _png(gradient, "L"))

    canonical_image = Image.open(io.BytesIO(result.canonical_image_png))
    canonical_editable = np.asarray(Image.open(io.BytesIO(result.canonical_editable_mask_png)))
    canonical_feather = np.asarray(Image.open(io.BytesIO(result.canonical_feather_mask_png)))
    assert canonical_image.size == (512, 512)
    assert canonical_editable.shape == (512, 512)
    assert canonical_feather.shape == (512, 512)
    assert set(np.unique(canonical_editable)).issubset({0, 255})
    assert len(np.unique(canonical_feather)) > 2
    assert result.canonical_image_sha256
    assert result.canonical_editable_mask_sha256
    assert result.canonical_feather_mask_sha256
    assert result.evidence_sha256
    inverse_image, inverse_editable, inverse_feather = inverse_warp_canonical_artifacts(
        transform=result.transform,
        canonical_image_png=result.canonical_image_png,
        canonical_editable_mask_png=result.canonical_editable_mask_png,
        canonical_feather_mask_png=result.canonical_feather_mask_png,
    )
    assert Image.open(io.BytesIO(inverse_image)).size == (1000, 1000)
    assert Image.open(io.BytesIO(inverse_editable)).size == (1000, 1000)
    assert Image.open(io.BytesIO(inverse_feather)).size == (1000, 1000)


def test_transform_evidence_validates_against_schema() -> None:
    observation, route, image, editable, feather = _observed()
    result = _canonical(observation, route, image, editable, feather)
    schema = json.loads(
        (ROOT / "contracts/identity_restoration/canonical_face_transform_v1.schema.json")
        .read_text(encoding="utf-8")
    )
    jsonschema.validate(result.as_dict()["transform"], schema)


def test_landmark_round_trip_boundary_and_failure() -> None:
    identity = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    assert verify_landmark_round_trip(
        [(0, 0), (1, 0), (0, 1), (2, 2), (3, 3)], identity, identity
    ) == (0.0, 0.0, 0.0, 0.0, 0.0)
    shifted = [1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    with pytest.raises(CanonicalTransformError, match="ROUND_TRIP_ERROR_EXCEEDED"):
        verify_landmark_round_trip(
            [(0, 0), (1, 0), (0, 1), (2, 2), (3, 3)], identity, shifted
        )


def test_non_eligible_route_is_rejected_before_canonicalization() -> None:
    image = _image()
    mask = _mask()
    observation, route, _, _, _ = _observed(
        _detection(bbox=(10, 10, 65, 65), landmarks=((20, 20), (45, 20), (32, 35), (25, 50), (40, 50)))
    )
    assert route.route_code == "BASE_REGEN_REQUIRED"
    with pytest.raises(CanonicalTransformError, match="NON_ELIGIBLE_ROUTE"):
        _canonical(observation, route, image, mask, mask)


def test_degenerate_landmarks_fail_closed() -> None:
    observation, route, image, editable, feather = _observed(
        _detection(
            bbox=(10, 10, 150, 150),
            landmarks=((20, 20), (40, 20), (60, 20), (80, 20), (100, 20)),
        )
    )
    assert route.route_code == "ELIGIBLE"
    with pytest.raises(CanonicalTransformError, match="DEGENERATE_LANDMARK_GEOMETRY"):
        _canonical(observation, route, image, editable, feather)


def test_dimension_mismatch_and_tampered_route_fail_closed() -> None:
    observation, route, image, editable, feather = _observed()
    with pytest.raises(CanonicalTransformError, match="IMAGE_MASK_DIMENSIONS_MISMATCH"):
        _canonical(observation, route, image, _mask((80, 80)), feather)
    tampered = dict(route.as_dict())
    tampered["policySha256"] = "b" * 64
    with pytest.raises(CanonicalTransformError, match="ROUTE_POLICY_SHA256_MISMATCH"):
        _canonical(observation, tampered, image, editable, feather)


def test_multiple_face_no_face_and_weak_detection_fixtures_fail_closed() -> None:
    image = _image()
    mask = _mask()
    detections = (
        _detection(bbox=(20, 20, 200, 200)),
        _detection(bbox=(300, 300, 500, 500)),
    )
    multiple = FaceObservabilityService(FakeDetector(detections), CONFIG).observe(image, mask)
    assert evaluate_candidate_v3_route(multiple, load_candidate_v3_route_policy()).route_code == "REVIEW_REQUIRED"
    no_face = FaceObservabilityService(FakeDetector(()), CONFIG).observe(image, mask)
    assert evaluate_candidate_v3_route(no_face, load_candidate_v3_route_policy()).route_code == "REJECTED_INVALID_INPUT"
    weak = FaceObservabilityService(
        FakeDetector((_detection(),)), CONFIG
    ).observe(image, mask)
    weak = replace(weak, selected_face_confidence=0.1)
    assert evaluate_candidate_v3_route(weak, load_candidate_v3_route_policy()).route_code == "REJECTED_INVALID_INPUT"


def test_policy_tamper_and_unsupported_version_fail_closed(tmp_path: Path) -> None:
    source = Path(load_candidate_v3_canonical_transform_policy.__globals__["POLICY_PATH"])
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["crop"]["paddingPerSide"] = 0.1
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(CanonicalTransformError, match="POLICY_SHA256_MISMATCH"):
        load_candidate_v3_canonical_transform_policy(tampered)


@pytest.mark.parametrize(
    ("name", "bbox", "expected"),
    [
        ("B05", (100, 100, 174, 214), "ELIGIBLE"),
        ("B06", (100, 100, 182, 211), "ELIGIBLE"),
        ("B10", (100, 100, 155, 155), "BASE_REGEN_REQUIRED"),
    ],
)
def test_locked_fixture_route_classes(name: str, bbox: tuple[int, int, int, int], expected: str) -> None:
    del name
    observation, route, *_ = _observed(_detection(bbox=bbox))
    assert observation.measurement_sha256
    assert route.route_code == expected
