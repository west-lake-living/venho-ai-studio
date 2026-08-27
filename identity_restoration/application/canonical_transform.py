from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Mapping

import cv2
import numpy as np
from PIL import Image, ImageOps

from .dto.candidate_v3 import (
    BoundingBox,
    CanonicalFaceTransform,
    Landmark,
    SourceImage,
)
from .candidate_v3_route_policy import load_candidate_v3_route_policy
from .face_observability import FaceObservability
from ..domain.policies.candidate_v3_route_policy import (
    CandidateV3RouteResult,
    evaluate_candidate_v3_route,
)


POLICY_PATH = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "candidate_v3_canonical_transform_policy_v1.json"
)
POLICY_ID = "candidate_v3_canonical_transform_policy"
POLICY_VERSION = "1.0"
TEMPLATE_ID = "candidate_v3_face_template"
TEMPLATE_VERSION = "1.0"
ROUTE_POLICY_SHA256 = "171019b8fcf62449b3f5d6af37372f9861eb80bd21a7b621ae89c760199fdb33"
MODEL_SIZE = 512
LANDMARK_NAMES = ("left_eye", "right_eye", "nose", "left_mouth", "right_mouth")


class CanonicalTransformError(ValueError):
    """Raised when Candidate v3 canonicalization cannot be trusted."""


@dataclass(frozen=True)
class CanonicalTransformPolicy:
    policy_id: str
    version: str
    template_id: str
    template_version: str
    template_sha256: str
    policy_sha256: str
    template_points: tuple[tuple[float, float], ...]
    padding_per_side: float
    border_mode: str
    image_interpolation: str
    binary_interpolation: str
    binary_threshold: float
    feather_interpolation: str
    round_trip_limit_px: float

    def template_payload(self) -> dict[str, Any]:
        return {
            "templateId": self.template_id,
            "version": self.template_version,
            "canvasSize": MODEL_SIZE,
            "landmarks": [
                {"name": name, "x": point[0], "y": point[1]}
                for name, point in zip(LANDMARK_NAMES, self.template_points)
            ],
        }

    def payload_without_hashes(self) -> dict[str, Any]:
        return {
            "policyId": self.policy_id,
            "version": self.version,
            "template": self.template_payload(),
            "crop": {
                "convention": "CP-B",
                "ratioReference": "max(face_bbox_width, face_bbox_height)",
                "paddingPerSide": self.padding_per_side,
                "shape": "SQUARE",
                "center": "FACE_BBOX_CENTER",
                "outOfBounds": "OOB-A",
                "transformOrder": "TO-A",
                "rasterization": {
                    "minimum": "floor",
                    "maximum": "ceil",
                    "preserveExtent": True,
                    "outsideSource": "REFLECT_101",
                },
            },
            "interpolation": {
                "image": self.image_interpolation,
                "binaryMask": self.binary_interpolation,
                "binaryThreshold": self.binary_threshold,
                "featherMask": self.feather_interpolation,
            },
            "borderMode": self.border_mode,
            "roundTrip": {
                "scope": "landmark point max Euclidean error",
                "maxErrorPx": self.round_trip_limit_px,
            },
            "templatePolicySha256": self.template_sha256,
        }


@dataclass(frozen=True)
class CanonicalizationResult:
    transform: CanonicalFaceTransform
    canonical_image_png: bytes
    canonical_editable_mask_png: bytes
    canonical_feather_mask_png: bytes
    canonical_image_sha256: str
    canonical_editable_mask_sha256: str
    canonical_feather_mask_sha256: str
    round_trip_errors_px: tuple[float, ...]
    max_round_trip_error_px: float
    raster_crop_box: tuple[int, int, int, int]
    template_id: str
    template_version: str
    template_sha256: str
    policy_id: str
    policy_version: str
    policy_sha256: str
    observation_measurement_sha256: str
    evidence_sha256: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "transform": _transform_dict(self.transform),
            "canonicalImageSha256": self.canonical_image_sha256,
            "canonicalEditableMaskSha256": self.canonical_editable_mask_sha256,
            "canonicalFeatherMaskSha256": self.canonical_feather_mask_sha256,
            "roundTripErrorsPx": list(self.round_trip_errors_px),
            "maxRoundTripErrorPx": self.max_round_trip_error_px,
            "rasterCropBox": {
                "left": self.raster_crop_box[0],
                "top": self.raster_crop_box[1],
                "right": self.raster_crop_box[2],
                "bottom": self.raster_crop_box[3],
            },
            "templateId": self.template_id,
            "templateVersion": self.template_version,
            "templateSha256": self.template_sha256,
            "policyId": self.policy_id,
            "policyVersion": self.policy_version,
            "policySha256": self.policy_sha256,
            "observationMeasurementSha256": self.observation_measurement_sha256,
            "evidenceSha256": self.evidence_sha256,
        }


def load_candidate_v3_canonical_transform_policy(
    path: Path = POLICY_PATH,
) -> CanonicalTransformPolicy:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CanonicalTransformError(f"canonical transform policy unavailable: {path}") from exc
    return _policy_from_payload(payload)


def canonicalize_candidate_v3(
    *,
    observation: FaceObservability,
    route_result: CandidateV3RouteResult | Mapping[str, Any],
    image_bytes: bytes,
    editable_mask_bytes: bytes,
    feather_mask_bytes: bytes,
    policy: CanonicalTransformPolicy | None = None,
) -> CanonicalizationResult:
    """Build deterministic CPU-only canonical image, masks, and evidence."""
    policy = policy or load_candidate_v3_canonical_transform_policy()
    _validate_policy(policy)
    _require_eligible_route(observation, route_result, policy)

    image = _decode_image(image_bytes)
    editable = _decode_mask(editable_mask_bytes)
    feather = _decode_mask(feather_mask_bytes)
    if editable.size != image.size or feather.size != image.size:
        raise CanonicalTransformError("IMAGE_MASK_DIMENSIONS_MISMATCH")
    if observation.image_width != image.width or observation.image_height != image.height:
        raise CanonicalTransformError("OBSERVATION_IMAGE_DIMENSIONS_MISMATCH")
    if observation.image_sha256 != _sha256(image_bytes):
        raise CanonicalTransformError("OBSERVATION_IMAGE_SHA256_MISMATCH")
    if observation.mask_sha256 != _sha256(editable_mask_bytes):
        raise CanonicalTransformError("OBSERVATION_MASK_SHA256_MISMATCH")

    source_points = _source_landmarks(observation)
    bbox = observation.selected_bbox
    if bbox is None:
        raise CanonicalTransformError("MISSING_SELECTED_BBOX")
    crop_box, raster_box = _crop_geometry(bbox, image.size, policy.padding_per_side)
    origin_x, origin_y, raster_width, raster_height = raster_box
    cropped_image = _reflect_crop(np.asarray(image), raster_box)
    cropped_editable = _reflect_crop(np.asarray(editable), raster_box)
    cropped_feather = _reflect_crop(np.asarray(feather), raster_box)
    crop_points = source_points - np.array([origin_x, origin_y], dtype=np.float64)
    template_points = np.asarray(policy.template_points, dtype=np.float64)
    crop_to_model = _estimate_similarity(crop_points, template_points)
    canvas_to_model = crop_to_model.copy()
    canvas_to_model[0, 2] -= crop_to_model[0, 0] * origin_x + crop_to_model[0, 1] * origin_y
    canvas_to_model[1, 2] -= crop_to_model[1, 0] * origin_x + crop_to_model[1, 1] * origin_y
    inverse = _invert_affine(canvas_to_model)
    errors = _round_trip_errors(source_points, canvas_to_model, inverse)
    max_error = max(errors, default=float("inf"))
    if not math.isfinite(max_error) or max_error > policy.round_trip_limit_px:
        raise CanonicalTransformError("ROUND_TRIP_ERROR_EXCEEDED")

    canonical_image = _warp(cropped_image, crop_to_model, cv2.INTER_LANCZOS4, policy.border_mode)
    canonical_editable = _warp(cropped_editable, crop_to_model, cv2.INTER_NEAREST, policy.border_mode)
    canonical_editable = np.where(
        canonical_editable.astype(np.float64) / 255.0 >= policy.binary_threshold,
        255,
        0,
    ).astype(np.uint8)
    canonical_feather = _warp(cropped_feather, crop_to_model, cv2.INTER_LINEAR, policy.border_mode)
    if canonical_image.shape[:2] != (MODEL_SIZE, MODEL_SIZE):
        raise CanonicalTransformError("CANONICAL_DIMENSIONS_INVALID")
    if not set(np.unique(canonical_editable)).issubset({0, 255}):
        raise CanonicalTransformError("BINARY_MASK_NOT_BINARY")

    image_png = _encode_png(canonical_image, "RGB")
    editable_png = _encode_png(canonical_editable, "L")
    feather_png = _encode_png(canonical_feather, "L")
    transform = CanonicalFaceTransform(
        version=POLICY_VERSION,
        source_image=SourceImage(image.width, image.height, _sha256(image_bytes)),
        canvas_crop_box=BoundingBox(*crop_box),
        model_size=MODEL_SIZE,
        landmark_set=tuple(
            Landmark(float(point[0]), float(point[1]), float(confidence))
            for point, confidence in zip(source_points, _landmark_confidences(observation))
        ),
        forward_matrix_3x3=tuple(float(value) for value in _to_3x3(canvas_to_model).ravel()),
        inverse_matrix_3x3=tuple(float(value) for value in _to_3x3(inverse).ravel()),
        border_mode=policy.border_mode,
        interpolation=policy.image_interpolation,
        transform_sha256="",
    )
    transform_hash = _sha256_canonical(_transform_dict(transform))
    transform = CanonicalFaceTransform(
        version=transform.version,
        source_image=transform.source_image,
        canvas_crop_box=transform.canvas_crop_box,
        model_size=transform.model_size,
        landmark_set=transform.landmark_set,
        forward_matrix_3x3=transform.forward_matrix_3x3,
        inverse_matrix_3x3=transform.inverse_matrix_3x3,
        border_mode=transform.border_mode,
        interpolation=transform.interpolation,
        transform_sha256=transform_hash,
    )
    validate_canonical_transform(transform, policy=policy)
    result_body = {
        "transform": _transform_dict(transform),
        "canonicalImageSha256": _sha256(image_png),
        "canonicalEditableMaskSha256": _sha256(editable_png),
        "canonicalFeatherMaskSha256": _sha256(feather_png),
        "roundTripErrorsPx": list(errors),
        "maxRoundTripErrorPx": max_error,
        "templateId": policy.template_id,
        "templateVersion": policy.template_version,
        "templateSha256": policy.template_sha256,
        "policyId": policy.policy_id,
        "policyVersion": policy.version,
        "policySha256": policy.policy_sha256,
        "observationMeasurementSha256": observation.measurement_sha256,
    }
    return CanonicalizationResult(
        transform=transform,
        canonical_image_png=image_png,
        canonical_editable_mask_png=editable_png,
        canonical_feather_mask_png=feather_png,
        canonical_image_sha256=_sha256(image_png),
        canonical_editable_mask_sha256=_sha256(editable_png),
        canonical_feather_mask_sha256=_sha256(feather_png),
        round_trip_errors_px=tuple(errors),
        max_round_trip_error_px=max_error,
        raster_crop_box=raster_box,
        template_id=policy.template_id,
        template_version=policy.template_version,
        template_sha256=policy.template_sha256,
        policy_id=policy.policy_id,
        policy_version=policy.version,
        policy_sha256=policy.policy_sha256,
        observation_measurement_sha256=observation.measurement_sha256,
        evidence_sha256=_sha256_canonical(result_body),
    )


def verify_landmark_round_trip(
    landmarks: tuple[tuple[float, float], ...] | list[tuple[float, float]],
    forward_matrix_3x3: tuple[float, ...] | list[float],
    inverse_matrix_3x3: tuple[float, ...] | list[float],
    *,
    limit_px: float = 0.5,
) -> tuple[float, ...]:
    """Verify the locked max Euclidean landmark round-trip invariant."""
    try:
        points = np.asarray(landmarks, dtype=np.float64)
        forward = np.asarray(forward_matrix_3x3, dtype=np.float64).reshape(3, 3)
        inverse = np.asarray(inverse_matrix_3x3, dtype=np.float64).reshape(3, 3)
    except (TypeError, ValueError) as exc:
        raise CanonicalTransformError("ROUND_TRIP_INPUT_INVALID") from exc
    if points.shape != (5, 2) or not np.isfinite(points).all():
        raise CanonicalTransformError("ROUND_TRIP_LANDMARKS_INVALID")
    if not np.isfinite(forward).all() or not np.isfinite(inverse).all():
        raise CanonicalTransformError("ROUND_TRIP_MATRIX_INVALID")
    errors = _round_trip_errors(points, forward[:2], inverse[:2])
    if max(errors, default=float("inf")) > limit_px:
        raise CanonicalTransformError("ROUND_TRIP_ERROR_EXCEEDED")
    return tuple(errors)


def validate_canonical_transform(
    transform: CanonicalFaceTransform,
    *,
    policy: CanonicalTransformPolicy | None = None,
) -> None:
    """Fail closed on tampered or structurally unsafe transform evidence."""
    policy = policy or load_candidate_v3_canonical_transform_policy()
    _validate_policy(policy)
    if transform.version != POLICY_VERSION or transform.model_size != MODEL_SIZE:
        raise CanonicalTransformError("TRANSFORM_VERSION_INVALID")
    if transform.border_mode != "REFLECT_101" or transform.interpolation != "LANCZOS4":
        raise CanonicalTransformError("TRANSFORM_INTERPOLATION_INVALID")
    if len(transform.landmark_set) != 5:
        raise CanonicalTransformError("LANDMARK_COUNT_INVALID")
    values = [
        transform.canvas_crop_box.left,
        transform.canvas_crop_box.top,
        transform.canvas_crop_box.right,
        transform.canvas_crop_box.bottom,
        *transform.forward_matrix_3x3,
        *transform.inverse_matrix_3x3,
    ]
    if not all(math.isfinite(float(value)) for value in values):
        raise CanonicalTransformError("TRANSFORM_EVIDENCE_NON_FINITE")
    if transform.canvas_crop_box.right <= transform.canvas_crop_box.left:
        raise CanonicalTransformError("CROP_BOUNDS_INVALID")
    if transform.canvas_crop_box.bottom <= transform.canvas_crop_box.top:
        raise CanonicalTransformError("CROP_BOUNDS_INVALID")
    if len(transform.forward_matrix_3x3) != 9 or len(transform.inverse_matrix_3x3) != 9:
        raise CanonicalTransformError("TRANSFORM_MATRIX_CARDINALITY_INVALID")
    if not re_fullmatch_sha(transform.source_image.sha256) or not re_fullmatch_sha(transform.transform_sha256):
        raise CanonicalTransformError("TRANSFORM_HASH_INVALID")
    expected = _sha256_canonical(
        _transform_dict(
            CanonicalFaceTransform(
                version=transform.version,
                source_image=transform.source_image,
                canvas_crop_box=transform.canvas_crop_box,
                model_size=transform.model_size,
                landmark_set=transform.landmark_set,
                forward_matrix_3x3=transform.forward_matrix_3x3,
                inverse_matrix_3x3=transform.inverse_matrix_3x3,
                border_mode=transform.border_mode,
                interpolation=transform.interpolation,
                transform_sha256="",
            )
        )
    )
    if expected != transform.transform_sha256:
        raise CanonicalTransformError("TRANSFORM_SHA256_MISMATCH")


class CanonicalFaceTransformService:
    """Application façade for the locked CPU-only canonicalization contract."""

    def __init__(self, policy: CanonicalTransformPolicy | None = None) -> None:
        self._policy = policy or load_candidate_v3_canonical_transform_policy()

    @property
    def policy(self) -> CanonicalTransformPolicy:
        return self._policy

    def canonicalize(
        self,
        *,
        observation: FaceObservability,
        route_result: CandidateV3RouteResult | Mapping[str, Any],
        image_bytes: bytes,
        editable_mask_bytes: bytes,
        feather_mask_bytes: bytes,
    ) -> CanonicalizationResult:
        return canonicalize_candidate_v3(
            observation=observation,
            route_result=route_result,
            image_bytes=image_bytes,
            editable_mask_bytes=editable_mask_bytes,
            feather_mask_bytes=feather_mask_bytes,
            policy=self._policy,
        )


def inverse_warp_canonical_artifacts(
    *,
    transform: CanonicalFaceTransform,
    canonical_image_png: bytes,
    canonical_editable_mask_png: bytes,
    canonical_feather_mask_png: bytes,
    policy: CanonicalTransformPolicy | None = None,
) -> tuple[bytes, bytes, bytes]:
    """Inverse-warp canonical image and masks into the immutable source canvas."""
    policy = policy or load_candidate_v3_canonical_transform_policy()
    validate_canonical_transform(transform, policy=policy)
    image = _decode_image(canonical_image_png)
    editable = _decode_mask(canonical_editable_mask_png)
    feather = _decode_mask(canonical_feather_mask_png)
    if image.size != (MODEL_SIZE, MODEL_SIZE) or editable.size != image.size or feather.size != image.size:
        raise CanonicalTransformError("CANONICAL_ARTIFACT_DIMENSIONS_INVALID")
    output_size = (transform.source_image.width, transform.source_image.height)
    inverse = np.asarray(transform.inverse_matrix_3x3, dtype=np.float64).reshape(3, 3)[:2]
    restored_image = _warp_to_size(np.asarray(image), inverse, cv2.INTER_LANCZOS4, output_size)
    restored_editable = _warp_to_size(np.asarray(editable), inverse, cv2.INTER_NEAREST, output_size)
    restored_editable = np.where(restored_editable >= 128, 255, 0).astype(np.uint8)
    restored_feather = _warp_to_size(np.asarray(feather), inverse, cv2.INTER_LINEAR, output_size)
    return (
        _encode_png(restored_image, "RGB"),
        _encode_png(restored_editable, "L"),
        _encode_png(restored_feather, "L"),
    )


def _policy_from_payload(payload: Any) -> CanonicalTransformPolicy:
    if not isinstance(payload, Mapping):
        raise CanonicalTransformError("POLICY_INVALID")
    try:
        template = payload["template"]
        landmarks = template["landmarks"]
        points = tuple((float(item["x"]), float(item["y"])) for item in landmarks)
        template_payload = {
            "templateId": template["templateId"],
            "version": template["version"],
            "canvasSize": template["canvasSize"],
            "landmarks": landmarks,
        }
        template_sha = payload["template"]["templateSha256"]
        policy = CanonicalTransformPolicy(
            policy_id=payload["policyId"],
            version=payload["version"],
            template_id=template["templateId"],
            template_version=template["version"],
            template_sha256=template_sha,
            policy_sha256=payload["policySha256"],
            template_points=points,
            padding_per_side=float(payload["crop"]["paddingPerSide"]),
            border_mode=payload["borderMode"],
            image_interpolation=payload["interpolation"]["image"],
            binary_interpolation=payload["interpolation"]["binaryMask"],
            binary_threshold=float(payload["interpolation"]["binaryThreshold"]),
            feather_interpolation=payload["interpolation"]["featherMask"],
            round_trip_limit_px=float(payload["roundTrip"]["maxErrorPx"]),
        )
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise CanonicalTransformError("POLICY_INVALID") from exc
    if _sha256_canonical(template_payload) != template_sha:
        raise CanonicalTransformError("TEMPLATE_SHA256_MISMATCH")
    if payload.get("templatePolicySha256") != template_sha:
        raise CanonicalTransformError("TEMPLATE_POLICY_SHA256_MISMATCH")
    if _sha256_canonical(policy.payload_without_hashes()) != policy.policy_sha256:
        raise CanonicalTransformError("POLICY_SHA256_MISMATCH")
    _validate_policy(policy)
    return policy


def _validate_policy(policy: CanonicalTransformPolicy) -> None:
    if policy.policy_id != POLICY_ID or policy.version != POLICY_VERSION:
        raise CanonicalTransformError("POLICY_VERSION_UNSUPPORTED")
    if policy.template_id != TEMPLATE_ID or policy.template_version != TEMPLATE_VERSION:
        raise CanonicalTransformError("TEMPLATE_VERSION_UNSUPPORTED")
    if len(policy.template_points) != 5 or not np.isfinite(policy.template_points).all():
        raise CanonicalTransformError("TEMPLATE_LANDMARKS_INVALID")
    if policy.padding_per_side != 0.2:
        raise CanonicalTransformError("CROP_PADDING_UNSUPPORTED")
    if policy.border_mode != "REFLECT_101":
        raise CanonicalTransformError("BORDER_MODE_UNSUPPORTED")
    if policy.image_interpolation != "LANCZOS4":
        raise CanonicalTransformError("IMAGE_INTERPOLATION_UNSUPPORTED")
    if policy.binary_interpolation != "NEAREST" or policy.feather_interpolation != "LINEAR":
        raise CanonicalTransformError("MASK_INTERPOLATION_UNSUPPORTED")
    if policy.binary_threshold != 0.5 or policy.round_trip_limit_px != 0.5:
        raise CanonicalTransformError("TRANSFORM_AUTHORITY_UNSUPPORTED")


def _require_eligible_route(
    observation: FaceObservability,
    route_result: CandidateV3RouteResult | Mapping[str, Any],
    policy: CanonicalTransformPolicy,
) -> None:
    route_code = getattr(route_result, "route_code", None)
    route_policy_id = getattr(route_result, "policy_id", None)
    route_policy_version = getattr(route_result, "policy_version", None)
    route_policy_sha = getattr(route_result, "policy_sha256", None)
    measurement_sha = getattr(route_result, "observation_measurement_sha256", None)
    decision_sha = getattr(route_result, "decision_sha256", None)
    if isinstance(route_result, Mapping):
        route_code = route_result.get("routeCode")
        route_policy_id = route_result.get("policyId")
        route_policy_version = route_result.get("policyVersion")
        route_policy_sha = route_result.get("policySha256")
        measurement_sha = route_result.get("observationMeasurementSha256")
        decision_sha = route_result.get("decisionSha256")
    if route_code != "ELIGIBLE":
        raise CanonicalTransformError("NON_ELIGIBLE_ROUTE")
    if route_policy_id != "candidate_v3_route_policy" or route_policy_version != "1.0":
        raise CanonicalTransformError("ROUTE_POLICY_VERSION_INVALID")
    if not isinstance(route_policy_sha, str) or not re_fullmatch_sha(route_policy_sha):
        raise CanonicalTransformError("ROUTE_POLICY_SHA256_INVALID")
    if route_policy_sha != ROUTE_POLICY_SHA256:
        raise CanonicalTransformError("ROUTE_POLICY_SHA256_MISMATCH")
    if not isinstance(measurement_sha, str) or measurement_sha != observation.measurement_sha256:
        raise CanonicalTransformError("ROUTE_OBSERVATION_LINEAGE_INVALID")
    if not observation.measurement_sha256:
        raise CanonicalTransformError("OBSERVATION_LINEAGE_INVALID")
    # Re-evaluate the immutable observation to ensure the supplied ELIGIBLE
    # result cannot bypass the locked route policy.
    try:
        route_policy = load_candidate_v3_route_policy()
    except Exception as exc:
        raise CanonicalTransformError("ROUTE_POLICY_UNAVAILABLE") from exc
    if route_policy.policy_sha256 != route_policy_sha:
        raise CanonicalTransformError("ROUTE_POLICY_SHA256_MISMATCH")
    checked = evaluate_candidate_v3_route(observation, route_policy)
    if checked.route_code != "ELIGIBLE":
        raise CanonicalTransformError("ROUTE_REEVALUATION_NOT_ELIGIBLE")
    if decision_sha is not None and decision_sha != checked.decision_sha256:
        raise CanonicalTransformError("ROUTE_DECISION_SHA256_MISMATCH")


def _decode_image(data: bytes) -> Image.Image:
    try:
        with Image.open(BytesIO(data)) as source:
            source.load()
            image = ImageOps.exif_transpose(source).convert("RGB")
    except Exception as exc:
        raise CanonicalTransformError("IMAGE_DECODE_FAILED") from exc
    if image.width <= 0 or image.height <= 0:
        raise CanonicalTransformError("IMAGE_DIMENSIONS_INVALID")
    return image


def _decode_mask(data: bytes) -> Image.Image:
    try:
        with Image.open(BytesIO(data)) as source:
            source.load()
            if source.mode not in {"1", "L", "I", "I;16", "F"}:
                raise ValueError("mask must be grayscale")
            mask = source.convert("L")
    except Exception as exc:
        raise CanonicalTransformError("MASK_DECODE_FAILED") from exc
    if mask.width <= 0 or mask.height <= 0:
        raise CanonicalTransformError("MASK_DIMENSIONS_INVALID")
    return mask


def _source_landmarks(observation: FaceObservability) -> np.ndarray:
    if len(observation.selected_landmarks) != 5:
        raise CanonicalTransformError("LANDMARK_COUNT_INVALID")
    points = np.asarray(observation.selected_landmarks, dtype=np.float64)
    if points.shape != (5, 2) or not np.isfinite(points).all():
        raise CanonicalTransformError("LANDMARKS_NON_FINITE")
    return points


def _landmark_confidences(observation: FaceObservability) -> tuple[float, ...]:
    if not observation.detected_faces:
        raise CanonicalTransformError("LANDMARK_CONFIDENCE_MISSING")
    landmarks = observation.detected_faces[0].get("landmarks", ())
    if len(landmarks) != 5:
        raise CanonicalTransformError("LANDMARK_COUNT_INVALID")
    confidence = observation.selected_face_confidence
    if confidence is None or not math.isfinite(float(confidence)):
        raise CanonicalTransformError("LANDMARK_CONFIDENCE_MISSING")
    return (float(confidence),) * 5


def _crop_geometry(
    bbox: tuple[float, float, float, float],
    image_size: tuple[int, int],
    padding_per_side: float,
) -> tuple[tuple[float, float, float, float], tuple[int, int, int, int]]:
    if len(bbox) != 4 or not np.isfinite(bbox).all():
        raise CanonicalTransformError("BBOX_INVALID")
    left, top, right, bottom = (float(value) for value in bbox)
    width, height = right - left, bottom - top
    if width <= 0 or height <= 0 or width > image_size[0] or height > image_size[1]:
        raise CanonicalTransformError("BBOX_DIMENSIONS_INVALID")
    side = 1.0 + 2.0 * padding_per_side
    requested_side = side * max(width, height)
    center_x, center_y = (left + right) / 2.0, (top + bottom) / 2.0
    crop = (
        center_x - requested_side / 2.0,
        center_y - requested_side / 2.0,
        center_x + requested_side / 2.0,
        center_y + requested_side / 2.0,
    )
    raster = (
        math.floor(crop[0]),
        math.floor(crop[1]),
        math.ceil(crop[2]),
        math.ceil(crop[3]),
    )
    if raster[2] <= raster[0] or raster[3] <= raster[1]:
        raise CanonicalTransformError("CROP_RASTER_INVALID")
    return crop, (raster[0], raster[1], raster[2], raster[3])


def _reflect_crop(array: np.ndarray, raster: tuple[int, int, int, int]) -> np.ndarray:
    left, top, right, bottom = raster
    height, width = array.shape[:2]
    if width <= 1 or height <= 1:
        raise CanonicalTransformError("REFLECT_SOURCE_TOO_SMALL")
    pad_left, pad_top = max(0, -left), max(0, -top)
    pad_right, pad_bottom = max(0, right - width), max(0, bottom - height)
    padded = cv2.copyMakeBorder(
        array,
        pad_top,
        pad_bottom,
        pad_left,
        pad_right,
        cv2.BORDER_REFLECT_101,
    )
    crop = padded[top + pad_top:bottom + pad_top, left + pad_left:right + pad_left]
    if crop.shape[1] != right - left or crop.shape[0] != bottom - top:
        raise CanonicalTransformError("REFLECT_CROP_DIMENSIONS_INVALID")
    return crop.copy()


def _estimate_similarity(source: np.ndarray, target: np.ndarray) -> np.ndarray:
    if source.shape != (5, 2) or target.shape != (5, 2):
        raise CanonicalTransformError("LANDMARK_COUNT_INVALID")
    source_mean = source.mean(axis=0)
    target_mean = target.mean(axis=0)
    source_centered = source - source_mean
    target_centered = target - target_mean
    variance = float(np.sum(source_centered * source_centered))
    if not math.isfinite(variance) or variance <= 1e-12:
        raise CanonicalTransformError("DEGENERATE_LANDMARK_GEOMETRY")
    covariance = source_centered.T @ target_centered
    if not np.isfinite(covariance).all():
        raise CanonicalTransformError("TRANSFORM_ESTIMATION_FAILED")
    try:
        u, singular, vt = np.linalg.svd(covariance)
    except np.linalg.LinAlgError as exc:
        raise CanonicalTransformError("TRANSFORM_ESTIMATION_FAILED") from exc
    if singular[-1] <= 1e-12 or not np.isfinite(singular).all():
        raise CanonicalTransformError("DEGENERATE_LANDMARK_GEOMETRY")
    rotation = vt.T @ u.T
    if np.linalg.det(rotation) < 0:
        vt[-1, :] *= -1
        rotation = vt.T @ u.T
    scale = float(np.sum(singular) / variance)
    matrix = scale * rotation
    translation = target_mean - matrix @ source_mean
    affine = np.array(
        [[matrix[0, 0], matrix[0, 1], translation[0]],
         [matrix[1, 0], matrix[1, 1], translation[1]]],
        dtype=np.float64,
    )
    if not np.isfinite(affine).all() or abs(np.linalg.det(matrix)) <= 1e-12:
        raise CanonicalTransformError("TRANSFORM_MATRIX_INVALID")
    if np.linalg.cond(matrix) > 1e8:
        raise CanonicalTransformError("TRANSFORM_MATRIX_CONDITION_INVALID")
    return affine


def _invert_affine(affine: np.ndarray) -> np.ndarray:
    matrix = _to_3x3(affine)
    if not np.isfinite(matrix).all():
        raise CanonicalTransformError("TRANSFORM_MATRIX_NON_FINITE")
    try:
        inverse = np.linalg.inv(matrix)
    except np.linalg.LinAlgError as exc:
        raise CanonicalTransformError("TRANSFORM_MATRIX_NON_INVERTIBLE") from exc
    if not np.isfinite(inverse).all():
        raise CanonicalTransformError("INVERSE_MATRIX_NON_FINITE")
    return inverse[:2]


def _round_trip_errors(points: np.ndarray, forward: np.ndarray, inverse: np.ndarray) -> tuple[float, ...]:
    homogeneous = np.column_stack((points, np.ones(len(points))))
    model = homogeneous @ _to_3x3(forward).T
    model = model[:, :2] / model[:, 2:3]
    restored = np.column_stack((model, np.ones(len(model)))) @ _to_3x3(inverse).T
    restored = restored[:, :2] / restored[:, 2:3]
    errors = np.linalg.norm(restored - points, axis=1)
    if not np.isfinite(errors).all():
        raise CanonicalTransformError("ROUND_TRIP_ERROR_INVALID")
    return tuple(float(error) for error in errors)


def _warp(array: np.ndarray, affine: np.ndarray, interpolation: int, border_mode: str) -> np.ndarray:
    if border_mode != "REFLECT_101":
        raise CanonicalTransformError("BORDER_MODE_UNSUPPORTED")
    return _warp_to_size(array, affine, interpolation, (MODEL_SIZE, MODEL_SIZE))


def _warp_to_size(
    array: np.ndarray,
    affine: np.ndarray,
    interpolation: int,
    output_size: tuple[int, int],
) -> np.ndarray:
    result = cv2.warpAffine(
        array,
        affine,
        output_size,
        flags=interpolation,
        borderMode=cv2.BORDER_REFLECT_101,
    )
    if result is None or result.shape[:2] != (output_size[1], output_size[0]):
        raise CanonicalTransformError("WARP_FAILED")
    return result


def _to_3x3(affine: np.ndarray) -> np.ndarray:
    if np.asarray(affine).shape == (3, 3):
        return np.asarray(affine, dtype=np.float64)
    return np.vstack((np.asarray(affine, dtype=np.float64), [0.0, 0.0, 1.0]))


def _transform_dict(transform: CanonicalFaceTransform) -> dict[str, Any]:
    return {
        "version": transform.version,
        "sourceImage": {
            "width": transform.source_image.width,
            "height": transform.source_image.height,
            "sha256": transform.source_image.sha256,
        },
        "canvasCropBox": {
            "left": transform.canvas_crop_box.left,
            "top": transform.canvas_crop_box.top,
            "right": transform.canvas_crop_box.right,
            "bottom": transform.canvas_crop_box.bottom,
        },
        "modelSize": transform.model_size,
        "landmarkSet": [
            {"x": landmark.x, "y": landmark.y, "confidence": landmark.confidence}
            for landmark in transform.landmark_set
        ],
        "forwardMatrix3x3": list(transform.forward_matrix_3x3),
        "inverseMatrix3x3": list(transform.inverse_matrix_3x3),
        "borderMode": transform.border_mode,
        "interpolation": transform.interpolation,
        "transformSha256": transform.transform_sha256,
    }


def _encode_png(array: np.ndarray, mode: str) -> bytes:
    try:
        del mode
        image = Image.fromarray(array)
        buffer = BytesIO()
        image.save(buffer, format="PNG", optimize=False, compress_level=9)
        return buffer.getvalue()
    except Exception as exc:
        raise CanonicalTransformError("ARTIFACT_ENCODING_FAILED") from exc


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_canonical(payload: Any) -> str:
    try:
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError) as exc:
        raise CanonicalTransformError("EVIDENCE_HASH_CONSTRUCTION_FAILED") from exc
    return _sha256(encoded)


def re_fullmatch_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)
