from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import jsonschema
import numpy as np
import pytest
from PIL import Image

from identity_restoration.application.face_observability import (
    MEASUREMENT_CONFIG_SHA256,
    FaceDetection,
    FaceObservabilityConfig,
    FaceObservabilityError,
    FaceObservabilityService,
)
from identity_restoration.infrastructure.face_observability_yunet import (
    PINNED_YUNET_CONFIG_SHA256,
    PINNED_YUNET_OBSERVABILITY_CONFIG,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
FACE_SCHEMA = json.loads(
    (REPO_ROOT / "contracts/identity_restoration/face_observability_v1.schema.json").read_text()
)
SHA = "a" * 64
CONFIG = FaceObservabilityConfig(
    detector_id="test-detector",
    detector_version="test-detector-v1",
    detector_config_sha256=SHA,
    measurement_config_sha256=SHA,
    minimum_confidence=0.6,
)


def _png(mode: str = "RGB", size: tuple[int, int] = (100, 100), color: object = None) -> bytes:
    if color is None:
        color = (20, 30, 40) if mode == "RGB" else 0
    image = Image.new(mode, size, color=color)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _detection(*, confidence: float = 0.95, bbox: tuple[float, float, float, float] = (20, 20, 80, 80), landmarks=None) -> FaceDetection:
    return FaceDetection(
        confidence=confidence,
        bbox=bbox,
        landmarks=landmarks or ((35, 40), (65, 40), (50, 52), (40, 65), (60, 65)),
        yaw_deg=2.0,
        pitch_deg=-1.0,
        roll_deg=0.5,
    )


class FakeDetector:
    def __init__(self, detections: tuple[FaceDetection, ...]) -> None:
        self.detections = detections

    def detect(self, image: Image.Image) -> tuple[FaceDetection, ...]:
        assert image.mode == "RGB"
        return self.detections


def _service(detections: tuple[FaceDetection, ...]) -> FaceObservabilityService:
    return FaceObservabilityService(FakeDetector(detections), CONFIG)


def test_identical_input_produces_identical_evidence_and_measurement_hash() -> None:
    image = _png()
    mask = _png(mode="L", color=255)
    first = _service((_detection(),)).observe(image, mask)
    second = _service((_detection(),)).observe(image, mask)

    assert first.as_dict() == second.as_dict()
    assert first.measurement_sha256 == second.measurement_sha256
    assert first.status == "VALID"


def test_malformed_image_fails_closed_with_explicit_evidence() -> None:
    evidence = _service((_detection(),)).observe(b"not-an-image", _png(mode="L", color=255))

    assert evidence.status == "INVALID"
    assert evidence.failure_reasons == ("MALFORMED_IMAGE",)
    jsonschema.validate(evidence.as_dict(), FACE_SCHEMA)


@pytest.mark.parametrize("mask", [b"not-a-mask", _png(mode="L", size=(80, 80), color=255)])
def test_malformed_or_mismatched_mask_fails_closed(mask: bytes) -> None:
    evidence = _service((_detection(),)).observe(_png(), mask)

    assert evidence.status == "INVALID"
    assert evidence.failure_reasons[0] in {"INVALID_MASK", "MASK_DIMENSIONS_MISMATCH"}
    jsonschema.validate(evidence.as_dict(), FACE_SCHEMA)


def test_no_face_is_explicitly_invalid() -> None:
    evidence = _service(()).observe(_png(), _png(mode="L", color=255))

    assert evidence.face_count == 0
    assert evidence.status == "INVALID"
    assert evidence.failure_reasons == ("NO_FACE_DETECTED",)


def test_multiple_faces_are_observed_deterministically_without_route_code() -> None:
    detections = (_detection(bbox=(60, 20, 90, 60)), _detection(bbox=(10, 20, 40, 60)))
    evidence = _service(detections).observe(_png(), _png(mode="L", color=255))

    assert evidence.face_count == 2
    assert evidence.selected_face_index is None
    assert evidence.status == "AMBIGUOUS"
    assert evidence.failure_reasons == ("MULTIPLE_FACES_DETECTED",)
    assert "ELIGIBLE" not in json.dumps(evidence.as_dict())


def test_confidence_is_preserved_and_weak_detection_fails_closed() -> None:
    evidence = _service((_detection(confidence=0.59),)).observe(_png(), _png(mode="L", color=255))

    assert evidence.selected_face_confidence == pytest.approx(0.59)
    assert evidence.status == "INVALID"
    assert evidence.failure_reasons == ("WEAK_DETECTION",)


def test_bbox_landmarks_and_mask_target_relationship_are_deterministic() -> None:
    image = _png()
    mask = _png(mode="L", color=0)
    mask_image = Image.open(io.BytesIO(mask)).copy()
    for x in range(20, 80):
        for y in range(20, 80):
            mask_image.putpixel((x, y), 255)
    output = io.BytesIO()
    mask_image.save(output, format="PNG")

    evidence = _service((_detection(),)).observe(image, output.getvalue())
    assert evidence.selected_bbox == (20.0, 20.0, 80.0, 80.0)
    assert len(evidence.selected_landmarks) == 5
    assert evidence.face_bbox_intersects_editable_mask is True
    assert evidence.face_center_inside_editable_mask is True
    assert evidence.face_bbox_mask_overlap_area_px > 0
    assert evidence.face_bbox_mask_overlap_ratio == pytest.approx(1.0)


@pytest.mark.parametrize(
    "detection,reason",
    [
        (_detection(bbox=(-1, 20, 80, 80)), "INVALID_BBOX"),
        (_detection(landmarks=((35, 40), (65, 40), (50, 52), (40, 65))), "INVALID_LANDMARKS"),
        (_detection(confidence=float("nan")), "INVALID_MEASUREMENTS"),
    ],
)
def test_invalid_bbox_landmarks_and_non_finite_measurements_fail_closed(
    detection: FaceDetection, reason: str
) -> None:
    evidence = _service((detection,)).observe(_png(), _png(mode="L", color=255))

    assert evidence.status == "INVALID"
    assert reason in evidence.failure_reasons


def test_schema_version_detector_identity_and_hashes_are_present() -> None:
    evidence = _service((_detection(),)).observe(_png(), _png(mode="L", color=255))
    payload = evidence.as_dict()

    assert payload["schemaVersion"] == "1.0"
    assert payload["detectorId"] == "test-detector"
    assert payload["detectorVersion"] == "test-detector-v1"
    assert payload["detectorConfigSha256"] == SHA
    assert payload["measurementConfigSha256"] == SHA
    assert len(payload["measurementSha256"]) == 64
    jsonschema.validate(payload, FACE_SCHEMA)


def test_output_is_immutable_and_as_dict_is_detached() -> None:
    evidence = _service((_detection(),)).observe(_png(), _png(mode="L", color=255))
    payload = evidence.as_dict()
    payload["failureReasons"].append("MUTATED")
    payload["detectedFaces"][0]["landmarks"][0]["x"] = 999

    assert evidence.failure_reasons == ()
    assert evidence.detected_faces[0]["landmarks"][0]["x"] == 35.0
    with pytest.raises(TypeError):
        evidence.detected_faces[0]["confidence"] = 0.0  # type: ignore[index]


def test_invalid_or_unpinned_observability_config_is_rejected() -> None:
    with pytest.raises(FaceObservabilityError):
        FaceObservabilityService(FakeDetector((_detection(),)), FaceObservabilityConfig(
            detector_id="",
            detector_version="v1",
            detector_config_sha256=SHA,
            measurement_config_sha256=SHA,
            minimum_confidence=0.6,
        ))


def test_detector_and_config_mismatch_is_rejected() -> None:
    detector = FakeDetector((_detection(),))
    detector.detector_id = "different-detector"
    with pytest.raises(FaceObservabilityError, match="detector/config mismatch"):
        FaceObservabilityService(detector, CONFIG)


def test_pinned_yunet_detector_and_measurement_configuration_are_repository_authority() -> None:
    model = REPO_ROOT / "models/geometry/yunet/face_detection_yunet_2023mar.onnx"
    assert model.is_file()
    assert hashlib.sha256(model.read_bytes()).hexdigest() == (
        "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"
    )
    assert PINNED_YUNET_OBSERVABILITY_CONFIG.detector_config_sha256 == PINNED_YUNET_CONFIG_SHA256
    assert PINNED_YUNET_OBSERVABILITY_CONFIG.measurement_config_sha256 == MEASUREMENT_CONFIG_SHA256
    assert PINNED_YUNET_OBSERVABILITY_CONFIG.minimum_confidence == 0.6
