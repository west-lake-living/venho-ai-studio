from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any, Mapping

from ...application.face_observability import FaceObservability


POLICY_ID = "candidate_v3_route_policy"
POLICY_VERSION = "1.0"
ROUTE_CODES = (
    "REJECTED_INVALID_INPUT",
    "BASE_REGEN_REQUIRED",
    "REVIEW_REQUIRED",
    "ELIGIBLE",
)
_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
_PRECEDENCE = (
    "REJECTED_INVALID_INPUT",
    "BASE_REGEN_REQUIRED",
    "REVIEW_REQUIRED",
    "ELIGIBLE",
)
_POSITIVE_CONDITIONS = (
    "input_structurally_valid",
    "exactly_one_eligible_face",
    "detector_config_pin_valid",
    "confidence_valid",
    "bbox_valid",
    "exactly_five_finite_landmarks",
    "interocular_distance_gt_zero",
    "measurements_finite",
    "mask_relation_valid",
    "face_area_ratio_gt_microface_threshold",
    "abs_yaw_lt_extreme_pose_threshold",
    "no_unresolved_ambiguity",
)


class RoutePolicyError(ValueError):
    """Raised when a route policy cannot be trusted or is unsupported."""


@dataclass(frozen=True)
class CandidateV3RoutePolicy:
    policy_id: str
    version: str
    microface_face_area_ratio: float
    extreme_pose_yaw_abs: float
    required_landmark_count: int
    interocular_minimum: float
    precedence: tuple[str, ...]
    positive_conditions: tuple[str, ...]
    policy_sha256: str

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "CandidateV3RoutePolicy":
        if not isinstance(payload, Mapping):
            raise RoutePolicyError("route policy must be a JSON object")
        policy_id = payload.get("policyId")
        version = payload.get("version")
        if policy_id != POLICY_ID:
            raise RoutePolicyError(f"unsupported policy ID: {policy_id!r}")
        if version != POLICY_VERSION:
            raise RoutePolicyError(f"unsupported policy version: {version!r}")

        declared_sha = payload.get("policySha256")
        if not isinstance(declared_sha, str) or not _SHA256_RE.fullmatch(declared_sha):
            raise RoutePolicyError("policy SHA-256 is invalid")
        actual_sha = sha256_canonical_policy(payload)
        if declared_sha != actual_sha:
            raise RoutePolicyError("policy SHA-256 mismatch")

        microface = payload.get("microface")
        extreme_pose = payload.get("extremePose")
        landmark_uncertainty = payload.get("landmarkUncertainty")
        precedence = payload.get("precedence")
        positive = payload.get("positiveEligible")
        if not all(isinstance(value, Mapping) for value in (microface, extreme_pose, landmark_uncertainty, positive)):
            raise RoutePolicyError("route policy sections are invalid")
        if not isinstance(precedence, list):
            raise RoutePolicyError("route policy precedence is invalid")
        precedence_codes = tuple(
            item.get("routeCode")
            for item in precedence
            if isinstance(item, Mapping)
        )
        if len(precedence) != len(_PRECEDENCE) or precedence_codes != _PRECEDENCE:
            raise RoutePolicyError("route policy precedence is unsupported")
        positive_conditions = positive.get("allOf")
        if positive.get("routeCode") != "ELIGIBLE" or positive.get("implicitFallback") is not False:
            raise RoutePolicyError("positive ELIGIBLE fallback is not fail-closed")
        if tuple(positive_conditions or ()) != _POSITIVE_CONDITIONS:
            raise RoutePolicyError("positive ELIGIBLE conditions are unsupported")

        _require_exact(microface, {
            "metric", "comparison", "threshold", "routeCode"
        }, "microface")
        _require_exact(extreme_pose, {
            "metric", "comparison", "threshold", "routeCode"
        }, "extreme pose")
        _require_exact(landmark_uncertainty, {
            "landmarkCountRequired", "interocularComparison", "interocularMinimum"
        }, "landmark uncertainty")
        if (
            microface.get("metric") != "face_area_ratio"
            or microface.get("comparison") != "<="
            or microface.get("routeCode") != "BASE_REGEN_REQUIRED"
            or microface.get("threshold") != 0.0030488715
            or extreme_pose.get("metric") != "abs(yaw)"
            or extreme_pose.get("comparison") != ">="
            or extreme_pose.get("routeCode") != "REVIEW_REQUIRED"
            or extreme_pose.get("threshold") != 79.361665
            or landmark_uncertainty.get("landmarkCountRequired") != 5
            or landmark_uncertainty.get("interocularComparison") != ">"
            or landmark_uncertainty.get("interocularMinimum") != 0
        ):
            raise RoutePolicyError("route policy calibration values are unsupported")

        return cls(
            policy_id=policy_id,
            version=version,
            microface_face_area_ratio=float(microface["threshold"]),
            extreme_pose_yaw_abs=float(extreme_pose["threshold"]),
            required_landmark_count=int(landmark_uncertainty["landmarkCountRequired"]),
            interocular_minimum=float(landmark_uncertainty["interocularMinimum"]),
            precedence=precedence_codes,
            positive_conditions=tuple(positive_conditions),
            policy_sha256=declared_sha,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "policyId": self.policy_id,
            "version": self.version,
            "microface": {
                "metric": "face_area_ratio",
                "comparison": "<=",
                "threshold": self.microface_face_area_ratio,
                "routeCode": "BASE_REGEN_REQUIRED",
            },
            "extremePose": {
                "metric": "abs(yaw)",
                "comparison": ">=",
                "threshold": self.extreme_pose_yaw_abs,
                "routeCode": "REVIEW_REQUIRED",
            },
            "landmarkUncertainty": {
                "landmarkCountRequired": self.required_landmark_count,
                "interocularComparison": ">",
                "interocularMinimum": (
                    0 if self.interocular_minimum == 0 else self.interocular_minimum
                ),
            },
            "precedence": [
                {"condition": "structurally_invalid_input", "routeCode": self.precedence[0]},
                {"condition": "microface_or_unrecoverable", "routeCode": self.precedence[1]},
                {
                    "condition": "unresolved_ambiguity_multiple_face_or_extreme_pose",
                    "routeCode": self.precedence[2],
                },
                {"condition": "explicit_all_pass_positive_proof", "routeCode": self.precedence[3]},
            ],
            "positiveEligible": {
                "allOf": list(self.positive_conditions),
                "routeCode": "ELIGIBLE",
                "implicitFallback": False,
            },
            "policySha256": self.policy_sha256,
        }


@dataclass(frozen=True)
class CandidateV3RouteResult:
    schema_version: str
    policy_id: str
    policy_version: str
    policy_sha256: str
    observation_measurement_sha256: str
    route_code: str
    reasons: tuple[str, ...]
    decision_sha256: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "policyId": self.policy_id,
            "policyVersion": self.policy_version,
            "policySha256": self.policy_sha256,
            "observationMeasurementSha256": self.observation_measurement_sha256,
            "routeCode": self.route_code,
            "reasons": list(self.reasons),
            "decisionSha256": self.decision_sha256,
        }


def evaluate_candidate_v3_route(
    observation: FaceObservability,
    policy: CandidateV3RoutePolicy,
) -> CandidateV3RouteResult:
    """Evaluate one immutable P2-T1 observation without I/O or detector execution."""
    policy_error = _policy_error(policy)
    if policy_error:
        return _result(observation, policy, "REJECTED_INVALID_INPUT", (policy_error,))

    observation_error = _observation_integrity_error(observation)
    if observation_error:
        return _result(observation, policy, "REJECTED_INVALID_INPUT", (observation_error,))

    structural_reasons = _structural_reasons(observation, policy)
    if structural_reasons:
        return _result(observation, policy, "REJECTED_INVALID_INPUT", structural_reasons)

    face_records = tuple(observation.detected_faces)
    microface = any(
        _face_area_ratio(face, observation.image_width, observation.image_height)
        <= policy.microface_face_area_ratio
        for face in face_records
    )
    if microface:
        return _result(observation, policy, "BASE_REGEN_REQUIRED", ("MICROFACE_FACE_AREA_RATIO",))

    if observation.face_count > 1 or observation.status == "AMBIGUOUS":
        return _result(observation, policy, "REVIEW_REQUIRED", ("MULTIPLE_FACES_AMBIGUOUS",))

    selected = face_records[0]
    yaw = selected.get("yawDeg")
    if abs(float(yaw)) >= policy.extreme_pose_yaw_abs:
        return _result(observation, policy, "REVIEW_REQUIRED", ("EXTREME_POSE_YAW",))

    positive_reasons = _positive_reasons(observation, selected, policy)
    if positive_reasons:
        return _result(observation, policy, "REJECTED_INVALID_INPUT", positive_reasons)
    return _result(observation, policy, "ELIGIBLE", ("POSITIVE_RULES_PASSED",))


def _result(
    observation: Any,
    policy: CandidateV3RoutePolicy,
    route_code: str,
    reasons: tuple[str, ...],
) -> CandidateV3RouteResult:
    measurement_sha = getattr(observation, "measurement_sha256", "")
    policy_id = getattr(policy, "policy_id", "")
    policy_version = getattr(policy, "version", "")
    policy_sha = getattr(policy, "policy_sha256", "")
    body = {
        "schemaVersion": "1.0",
        "policyId": policy_id,
        "policyVersion": policy_version,
        "policySha256": policy_sha,
        "observationMeasurementSha256": measurement_sha,
        "routeCode": route_code,
        "reasons": list(reasons),
    }
    return CandidateV3RouteResult(
        schema_version="1.0",
        policy_id=policy_id,
        policy_version=policy_version,
        policy_sha256=policy_sha,
        observation_measurement_sha256=measurement_sha,
        route_code=route_code,
        reasons=tuple(reasons),
        decision_sha256=_sha256_canonical(body),
    )


def _policy_error(policy: Any) -> str | None:
    if not isinstance(policy, CandidateV3RoutePolicy):
        return "UNSUPPORTED_POLICY"
    if policy.policy_id != POLICY_ID:
        return "UNSUPPORTED_POLICY_ID"
    if policy.version != POLICY_VERSION:
        return "UNSUPPORTED_POLICY_VERSION"
    try:
        payload = policy.as_dict()
        if not _SHA256_RE.fullmatch(policy.policy_sha256):
            return "INVALID_POLICY_SHA256"
        if sha256_canonical_policy(payload) != policy.policy_sha256:
            return "POLICY_SHA256_MISMATCH"
        CandidateV3RoutePolicy.from_payload(payload)
    except (IndexError, TypeError, ValueError, RoutePolicyError):
        return "INVALID_POLICY"
    return None


def _observation_integrity_error(observation: Any) -> str | None:
    if not isinstance(observation, FaceObservability):
        return "INVALID_OBSERVATION_TYPE"
    if observation.schema_version != "1.0":
        return "UNSUPPORTED_OBSERVATION_SCHEMA_VERSION"
    try:
        payload = observation.as_dict()
        declared = observation.measurement_sha256
        if not isinstance(declared, str) or not _SHA256_RE.fullmatch(declared):
            return "INVALID_OBSERVATION_MEASUREMENT_SHA256"
        payload.pop("measurementSha256", None)
        if _sha256_canonical(payload) != declared:
            return "OBSERVATION_MEASUREMENT_SHA256_MISMATCH"
    except (TypeError, ValueError, OverflowError):
        return "INVALID_OBSERVATION_MEASUREMENTS"
    return None


def _structural_reasons(
    observation: FaceObservability,
    policy: CandidateV3RoutePolicy,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if observation.status == "INVALID":
        reasons.extend(_stable_observation_failure_reasons(observation.failure_reasons))
        if not reasons:
            reasons.append("INVALID_OBSERVATION_STATUS")
    if observation.image_width <= 0 or observation.image_height <= 0:
        reasons.append("INVALID_IMAGE_DIMENSIONS")
    if observation.mask_width != observation.image_width or observation.mask_height != observation.image_height:
        reasons.append("INVALID_MASK_DIMENSIONS")
    if not _valid_sha(observation.mask_sha256):
        reasons.append("INVALID_MASK_EVIDENCE")
    if not observation.detector_id or not observation.detector_version:
        reasons.append("INVALID_DETECTOR_CONFIG_PIN")
    if not _valid_sha(observation.detector_config_sha256) or not _valid_sha(observation.measurement_config_sha256):
        reasons.append("INVALID_DETECTOR_CONFIG_PIN")
    if not isinstance(observation.face_count, int) or isinstance(observation.face_count, bool) or observation.face_count < 0:
        reasons.append("INVALID_FACE_COUNT")
    if observation.face_count != len(observation.detected_faces):
        reasons.append("FACE_COUNT_MISMATCH")
    for face in observation.detected_faces:
        reasons.extend(_face_record_reasons(face, observation.image_width, observation.image_height, policy))
    if observation.face_count == 0:
        reasons.append("NO_FACE_DETECTED")
    if observation.face_count == 1:
        if observation.status != "VALID":
            reasons.append("INVALID_OBSERVATION_STATUS")
        if observation.selected_face_index != 0:
            reasons.append("INVALID_SELECTED_FACE")
        if observation.selected_bbox is None or len(observation.selected_landmarks) != policy.required_landmark_count:
            reasons.append("INVALID_SELECTED_FACE")
        if not _valid_confidence(observation.selected_face_confidence):
            reasons.append("INVALID_CONFIDENCE")
        if len(observation.detected_faces) == 1:
            if _bbox_values(observation.selected_bbox) != _bbox_values(observation.detected_faces[0].get("bbox")):
                reasons.append("SELECTED_FACE_MISMATCH")
            if _landmark_values(observation.selected_landmarks) != _landmark_values(
                observation.detected_faces[0].get("landmarks", ())
            ):
                reasons.append("SELECTED_FACE_MISMATCH")
    elif observation.face_count > 1 and observation.status not in {"AMBIGUOUS", "VALID"}:
        reasons.append("INVALID_OBSERVATION_STATUS")
    return _dedupe(reasons)


def _positive_reasons(
    observation: FaceObservability,
    selected: Mapping[str, Any],
    policy: CandidateV3RoutePolicy,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if observation.status != "VALID" or observation.face_count != 1:
        reasons.append("MISSING_POSITIVE_PROOF")
    if not _valid_mask_relation(observation):
        reasons.append("INVALID_MASK_RELATION")
    interocular = observation.interocular_distance_px
    if not _finite_positive(interocular, policy.interocular_minimum):
        reasons.append("INVALID_INTEROCULAR_DISTANCE")
    area_ratio = _face_area_ratio(selected, observation.image_width, observation.image_height)
    if not math.isfinite(area_ratio) or area_ratio <= policy.microface_face_area_ratio:
        reasons.append("MICROFACE_FACE_AREA_RATIO")
    yaw = selected.get("yawDeg")
    if not _finite(yaw):
        reasons.append("INVALID_YAW")
    elif abs(float(yaw)) >= policy.extreme_pose_yaw_abs:
        reasons.append("EXTREME_POSE_YAW")
    if not _finite(observation.face_center_x) or not _finite(observation.face_center_y):
        reasons.append("INVALID_FACE_MEASUREMENTS")
    return _dedupe(reasons)


def _face_record_reasons(
    face: Any,
    image_width: int,
    image_height: int,
    policy: CandidateV3RoutePolicy,
) -> list[str]:
    if not isinstance(face, Mapping):
        return ["INVALID_FACE_RECORD"]
    reasons: list[str] = []
    if not _valid_confidence(face.get("confidence")):
        reasons.append("INVALID_CONFIDENCE")
    bbox = face.get("bbox")
    if not _valid_bbox(bbox, image_width, image_height):
        reasons.append("INVALID_BBOX")
    landmarks = face.get("landmarks")
    if not isinstance(landmarks, (tuple, list)) or len(landmarks) != policy.required_landmark_count:
        reasons.append("INVALID_LANDMARKS")
    elif any(
        not isinstance(point, Mapping)
        or not _finite(point.get("x"))
        or not _finite(point.get("y"))
        or point["x"] < 0
        or point["y"] < 0
        or point["x"] > image_width
        or point["y"] > image_height
        for point in landmarks
    ):
        reasons.append("INVALID_LANDMARKS")
    for key in ("yawDeg", "pitchDeg", "rollDeg"):
        if face.get(key) is not None and not _finite(face.get(key)):
            reasons.append("INVALID_MEASUREMENTS")
    return reasons


def _valid_mask_relation(observation: FaceObservability) -> bool:
    values = (
        observation.face_bbox_intersects_editable_mask is True,
        observation.face_center_inside_editable_mask is True,
        isinstance(observation.face_bbox_mask_overlap_area_px, int)
        and observation.face_bbox_mask_overlap_area_px > 0,
        _finite_positive(observation.face_bbox_mask_overlap_ratio, 0),
        isinstance(observation.editable_mask_nonzero_pixel_count, int)
        and observation.editable_mask_nonzero_pixel_count > 0,
        _finite_positive(observation.editable_mask_coverage_ratio, 0),
    )
    return all(values)


def _valid_bbox(bbox: Any, width: int, height: int) -> bool:
    values = _bbox_values(bbox)
    if values is None:
        return False
    left, top, right, bottom = values
    return (
        all(_finite(value) for value in values)
        and 0 <= left < right <= width
        and 0 <= top < bottom <= height
    )


def _valid_confidence(value: Any) -> bool:
    return _finite(value) and 0 <= float(value) <= 1


def _face_area_ratio(face: Mapping[str, Any], width: int, height: int) -> float:
    bbox = face.get("bbox")
    if not _valid_bbox(bbox, width, height) or width <= 0 or height <= 0:
        return math.nan
    values = _bbox_values(bbox)
    assert values is not None
    return ((values[2] - values[0]) * (values[3] - values[1])) / float(width * height)


def _bbox_values(bbox: Any) -> tuple[float, float, float, float] | None:
    if isinstance(bbox, Mapping):
        values = tuple(bbox.get(key) for key in ("left", "top", "right", "bottom"))
    elif isinstance(bbox, (tuple, list)) and len(bbox) == 4:
        values = tuple(bbox)
    else:
        return None
    if len(values) != 4:
        return None
    return values  # type: ignore[return-value]


def _landmark_values(landmarks: Any) -> tuple[tuple[float, float], ...]:
    if not isinstance(landmarks, (tuple, list)):
        return ()
    values: list[tuple[float, float]] = []
    for point in landmarks:
        if isinstance(point, Mapping):
            values.append((point.get("x"), point.get("y")))  # type: ignore[arg-type]
        elif isinstance(point, (tuple, list)) and len(point) == 2:
            values.append((point[0], point[1]))
        else:
            return ()
    return tuple(values)


def _stable_observation_failure_reasons(reasons: tuple[str, ...]) -> list[str]:
    mapping = {
        "MALFORMED_IMAGE": "MALFORMED_IMAGE",
        "INVALID_MASK": "INVALID_MASK_EVIDENCE",
        "MASK_DIMENSIONS_MISMATCH": "INVALID_MASK_DIMENSIONS",
        "DETECTOR_FAILURE": "DETECTOR_FAILURE",
        "NO_FACE_DETECTED": "NO_FACE_DETECTED",
        "MULTIPLE_FACES_DETECTED": "MULTIPLE_FACES_AMBIGUOUS",
        "WEAK_DETECTION": "INVALID_CONFIDENCE",
        "INVALID_BBOX": "INVALID_BBOX",
        "INVALID_LANDMARKS": "INVALID_LANDMARKS",
        "INVALID_MEASUREMENTS": "INVALID_MEASUREMENTS",
    }
    return [mapping.get(reason, "INVALID_OBSERVATION") for reason in reasons]


def _require_exact(section: Mapping[str, Any], keys: set[str], label: str) -> None:
    if set(section) != keys:
        raise RoutePolicyError(f"{label} policy shape is unsupported")


def _sha256_canonical(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def sha256_canonical_policy(payload: Mapping[str, Any]) -> str:
    body = dict(payload)
    body.pop("policySha256", None)
    return _sha256_canonical(body)


def _valid_sha(value: Any) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _finite(value: Any) -> bool:
    try:
        return value is not None and math.isfinite(float(value))
    except (TypeError, ValueError, OverflowError):
        return False


def _finite_positive(value: Any, minimum: float) -> bool:
    return _finite(value) and float(value) > minimum


def _dedupe(reasons: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(reasons))


class CandidateV3RoutePolicyEvaluator:
    """Small application-neutral façade around the pure route function."""

    def __init__(self, policy: CandidateV3RoutePolicy) -> None:
        self._policy = policy

    def evaluate(self, observation: FaceObservability) -> CandidateV3RouteResult:
        return evaluate_candidate_v3_route(observation, self._policy)
