from __future__ import annotations

import hashlib
import io
import json
import math
from dataclasses import replace
from dataclasses import FrozenInstanceError
from pathlib import Path

import jsonschema
import pytest
from PIL import Image

from identity_restoration.application.face_observability import (
    FaceDetection,
    FaceObservabilityConfig,
    FaceObservabilityService,
)
from identity_restoration.application.candidate_v3_route_policy import (
    load_candidate_v3_route_policy,
)
from identity_restoration.domain.policies.candidate_v3_route_policy import (
    CandidateV3RoutePolicy,
    CandidateV3RoutePolicyEvaluator,
    RoutePolicyError,
    evaluate_candidate_v3_route,
    sha256_canonical_policy,
)


ROOT = Path(__file__).resolve().parents[3]
ROUTE_SCHEMA = json.loads(
    (ROOT / "contracts/identity_restoration/candidate_v3_route_result_v1.schema.json")
    .read_text(encoding="utf-8")
)
SHA = "a" * 64
CONFIG = FaceObservabilityConfig(
    detector_id="test-detector",
    detector_version="test-detector-v1",
    detector_config_sha256=SHA,
    measurement_config_sha256=SHA,
    minimum_confidence=0.6,
)


def _png(size: tuple[int, int] = (1000, 1000), mode: str = "RGB", color: object = None) -> bytes:
    if color is None:
        color = (20, 30, 40) if mode == "RGB" else 255
    image = Image.new(mode, size, color=color)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _detection(
    *,
    bbox: tuple[float, float, float, float] = (100, 100, 300, 300),
    yaw: float | None = 0.0,
    landmarks: tuple[tuple[float, float], ...] | None = None,
    confidence: float = 0.95,
) -> FaceDetection:
    return FaceDetection(
        confidence=confidence,
        bbox=bbox,
        landmarks=landmarks or ((150, 170), (250, 170), (200, 220), (170, 270), (230, 270)),
        yaw_deg=yaw,
        pitch_deg=-1.0,
        roll_deg=0.5,
    )


class FakeDetector:
    def __init__(self, detections: tuple[FaceDetection, ...]) -> None:
        self.detections = detections

    def detect(self, image: Image.Image) -> tuple[FaceDetection, ...]:
        return self.detections


def _observe(*detections: FaceDetection, size: tuple[int, int] = (1000, 1000)):
    service = FaceObservabilityService(FakeDetector(tuple(detections)), CONFIG)
    return service.observe(_png(size), _png(size, mode="L"))


@pytest.fixture(scope="module")
def policy() -> CandidateV3RoutePolicy:
    return load_candidate_v3_route_policy()


def _assert_schema(result) -> None:
    jsonschema.validate(result.as_dict(), ROUTE_SCHEMA)


def _rehash(observation, **changes):
    changed = replace(observation, **changes, measurement_sha256="pending")
    payload = changed.as_dict()
    payload.pop("measurementSha256")
    measurement_sha = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()
    ).hexdigest()
    return replace(changed, measurement_sha256=measurement_sha)


def test_policy_is_loaded_from_the_pinned_server_owned_config(policy) -> None:
    assert policy.policy_id == "candidate_v3_route_policy"
    assert policy.version == "1.0"
    assert policy.microface_face_area_ratio == 0.0030488715
    assert policy.extreme_pose_yaw_abs == 79.361665
    assert policy.precedence == (
        "REJECTED_INVALID_INPUT",
        "BASE_REGEN_REQUIRED",
        "REVIEW_REQUIRED",
        "ELIGIBLE",
    )
    assert sha256_canonical_policy(policy.as_dict()) == policy.policy_sha256


def test_policy_hash_is_stable_and_invalid_payloads_fail_closed(policy) -> None:
    assert policy.policy_sha256 == load_candidate_v3_route_policy().policy_sha256
    payload = policy.as_dict()
    payload["policySha256"] = "0" * 64
    with pytest.raises(RoutePolicyError, match="mismatch"):
        CandidateV3RoutePolicy.from_payload(payload)


def test_identical_observation_and_policy_produce_identical_result(policy) -> None:
    observation = _observe(_detection())
    first = evaluate_candidate_v3_route(observation, policy)
    second = evaluate_candidate_v3_route(observation, policy)

    assert first.as_dict() == second.as_dict()
    assert first.reasons == second.reasons
    assert first.decision_sha256 == second.decision_sha256
    _assert_schema(first)


@pytest.mark.parametrize(
    "observation,reason",
    [
        (_observe(_detection()).__class__, "INVALID_OBSERVATION_TYPE"),
    ],
)
def test_invalid_observation_type_fails_closed(policy, observation, reason) -> None:
    result = evaluate_candidate_v3_route(observation, policy)
    assert result.route_code == "REJECTED_INVALID_INPUT"
    assert result.reasons == (reason,)


def test_malformed_observation_invalid_mask_and_no_face_route_to_rejection(policy) -> None:
    malformed = FaceObservabilityService(FakeDetector(()), CONFIG).observe(b"bad", _png(mode="L"))
    invalid_mask = FaceObservabilityService(FakeDetector(()), CONFIG).observe(_png(), b"bad")
    no_face = _observe()

    for observation in (malformed, invalid_mask, no_face):
        result = evaluate_candidate_v3_route(observation, policy)
        assert result.route_code == "REJECTED_INVALID_INPUT"
        _assert_schema(result)


def test_multiple_faces_are_reviewed_after_structural_checks(policy) -> None:
    observation = _observe(
        _detection(bbox=(100, 100, 300, 300)),
        _detection(bbox=(500, 500, 700, 700)),
    )
    result = evaluate_candidate_v3_route(observation, policy)
    assert result.route_code == "REVIEW_REQUIRED"
    assert result.reasons == ("MULTIPLE_FACES_AMBIGUOUS",)


def test_microface_threshold_equality_and_precedence_beat_extreme_pose(policy) -> None:
    width = 55.0
    height = policy.microface_face_area_ratio * 1_000_000 / width
    height = math.nextafter(height, 0.0)
    observation = _observe(
        _detection(bbox=(100, 100, 100 + width, 100 + height), yaw=policy.extreme_pose_yaw_abs)
    )
    assert ((width * height) / 1_000_000) <= policy.microface_face_area_ratio
    assert ((width * height) / 1_000_000) == pytest.approx(policy.microface_face_area_ratio)
    result = evaluate_candidate_v3_route(observation, policy)
    assert result.route_code == "BASE_REGEN_REQUIRED"
    assert result.reasons == ("MICROFACE_FACE_AREA_RATIO",)


def test_value_just_above_microface_threshold_does_not_trigger_microface(policy) -> None:
    bbox = (100, 100, 155, 156)
    observation = _observe(_detection(bbox=bbox, yaw=0.0))
    assert ((bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) / 1_000_000) > policy.microface_face_area_ratio
    assert evaluate_candidate_v3_route(observation, policy).route_code == "ELIGIBLE"


def test_b10_locked_shape_routes_to_base_regeneration_and_yaw_is_lower_precedence(policy) -> None:
    observation = _observe(
        _detection(bbox=(100, 100, 155, 155), yaw=policy.extreme_pose_yaw_abs)
    )
    result = evaluate_candidate_v3_route(observation, policy)
    assert result.route_code == "BASE_REGEN_REQUIRED"
    assert "EXTREME_POSE_YAW" not in result.reasons


def test_extreme_pose_boundary_and_below_boundary(policy) -> None:
    boundary = evaluate_candidate_v3_route(
        _observe(_detection(yaw=policy.extreme_pose_yaw_abs)), policy
    )
    below = evaluate_candidate_v3_route(
        _observe(_detection(yaw=policy.extreme_pose_yaw_abs - 0.000001)), policy
    )
    assert boundary.route_code == "REVIEW_REQUIRED"
    assert boundary.reasons == ("EXTREME_POSE_YAW",)
    assert below.route_code == "ELIGIBLE"


def test_b05_and_b06_locked_measurement_classes_are_eligible_with_all_positive_proof(policy) -> None:
    b05 = _observe(_detection(bbox=(100, 100, 174, 214), yaw=-49.077421))
    b06 = _observe(_detection(bbox=(100, 100, 182, 211), yaw=-7.586991))

    assert evaluate_candidate_v3_route(b05, policy).route_code == "ELIGIBLE"
    assert evaluate_candidate_v3_route(b06, policy).route_code == "ELIGIBLE"


@pytest.mark.parametrize(
    "observation_factory",
    [
        lambda: _observe(_detection(landmarks=((150, 170), (250, 170), (200, 220), (170, 270)))),
        lambda: _observe(_detection(landmarks=((150, 170), (150, 170), (200, 220), (170, 270), (230, 270)))),
    ],
)
def test_invalid_landmark_count_or_non_positive_interocular_fails_closed(policy, observation_factory) -> None:
    result = evaluate_candidate_v3_route(observation_factory(), policy)
    assert result.route_code == "REJECTED_INVALID_INPUT"
    assert any(reason in result.reasons for reason in ("INVALID_LANDMARKS", "INVALID_INTEROCULAR_DISTANCE"))


def test_missing_positive_mask_proof_never_defaults_to_eligible(policy) -> None:
    observation = _rehash(_observe(_detection()), face_center_inside_editable_mask=False)
    result = evaluate_candidate_v3_route(observation, policy)
    assert result.route_code == "REJECTED_INVALID_INPUT"
    assert "INVALID_MASK_RELATION" in result.reasons


def test_non_finite_landmark_and_invalid_observation_hash_fail_closed(policy) -> None:
    observation = _observe(_detection())
    tampered = replace(observation, selected_landmarks=((float("nan"), 170.0),) + observation.selected_landmarks[1:])
    result = evaluate_candidate_v3_route(tampered, policy)
    assert result.route_code == "REJECTED_INVALID_INPUT"
    assert result.reasons in {
        ("OBSERVATION_MEASUREMENT_SHA256_MISMATCH",),
        ("INVALID_OBSERVATION_MEASUREMENTS",),
    }


@pytest.mark.parametrize(
    "policy_change,reason",
    [
        ({"policy_sha256": "0" * 64}, "POLICY_SHA256_MISMATCH"),
        ({"version": "9.9"}, "UNSUPPORTED_POLICY_VERSION"),
        ({"policy_id": "other_policy"}, "UNSUPPORTED_POLICY_ID"),
    ],
)
def test_policy_tamper_and_unsupported_identity_fail_closed(policy, policy_change, reason) -> None:
    tampered = replace(policy, **policy_change)
    result = evaluate_candidate_v3_route(_observe(_detection()), tampered)
    assert result.route_code == "REJECTED_INVALID_INPUT"
    assert result.reasons == (reason,)


def test_result_is_immutable_and_links_observation_measurement(policy) -> None:
    observation = _observe(_detection())
    result = CandidateV3RoutePolicyEvaluator(policy).evaluate(observation)
    assert result.observation_measurement_sha256 == observation.measurement_sha256
    assert result.as_dict()["policySha256"] == policy.policy_sha256
    with pytest.raises(FrozenInstanceError):
        result.reasons += ("MUTATED",)  # type: ignore[misc]
