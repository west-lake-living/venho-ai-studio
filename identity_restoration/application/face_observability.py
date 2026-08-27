from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from io import BytesIO
from types import MappingProxyType
from typing import Any, Mapping, Protocol

import numpy as np
from PIL import Image, ImageOps


class FaceObservabilityError(ValueError):
    """Raised when the CPU observability contract cannot be constructed."""


@dataclass(frozen=True)
class FaceDetection:
    """Detector output in source-image coordinates.

    Concrete detector details stay behind this application boundary. The
    five-point order is the existing project convention: left eye, right eye,
    nose, left mouth corner, right mouth corner.
    """

    confidence: float
    bbox: tuple[float, float, float, float]
    landmarks: tuple[tuple[float, float], ...]
    yaw_deg: float | None = None
    pitch_deg: float | None = None
    roll_deg: float | None = None


class FaceDetector(Protocol):
    def detect(self, image: Image.Image) -> tuple[FaceDetection, ...]:
        """Return all detector candidates without making a route decision."""


@dataclass(frozen=True)
class FaceObservabilityConfig:
    detector_id: str
    detector_version: str
    detector_config_sha256: str
    measurement_config_sha256: str
    minimum_confidence: float


@dataclass(frozen=True)
class FaceObservability:
    schema_version: str
    image_sha256: str
    image_width: int
    image_height: int
    mask_sha256: str
    mask_width: int
    mask_height: int
    detector_id: str
    detector_version: str
    detector_config_sha256: str
    measurement_config_sha256: str
    face_count: int
    selected_face_index: int | None
    selected_face_confidence: float | None
    selected_bbox: tuple[float, float, float, float] | None
    selected_landmarks: tuple[tuple[float, float], ...]
    detected_faces: tuple[Mapping[str, Any], ...]
    interocular_distance_px: float | None
    face_center_x: float | None
    face_center_y: float | None
    border_clipped: bool | None
    face_bbox_intersects_editable_mask: bool | None
    face_bbox_mask_overlap_area_px: int | None
    face_bbox_mask_overlap_ratio: float | None
    editable_mask_nonzero_pixel_count: int | None
    editable_mask_coverage_ratio: float | None
    face_center_inside_editable_mask: bool | None
    status: str
    quality_tier: str
    failure_reasons: tuple[str, ...]
    measurement_sha256: str

    def as_dict(self) -> dict[str, Any]:
        """Return a fresh JSON-compatible copy; mutating it cannot mutate this DTO."""
        return {
            "schemaVersion": self.schema_version,
            "imageSha256": self.image_sha256,
            "imageWidth": self.image_width,
            "imageHeight": self.image_height,
            "maskSha256": self.mask_sha256,
            "maskWidth": self.mask_width,
            "maskHeight": self.mask_height,
            "detectorId": self.detector_id,
            "detectorVersion": self.detector_version,
            "detectorConfigSha256": self.detector_config_sha256,
            "measurementConfigSha256": self.measurement_config_sha256,
            "faceCount": self.face_count,
            "selectedFaceIndex": self.selected_face_index,
            "selectedFaceConfidence": self.selected_face_confidence,
            "bbox": _bbox_dict(self.selected_bbox),
            "landmarks": _landmark_dicts(self.selected_landmarks),
            "detectedFaces": [_json_detection(face) for face in self.detected_faces],
            "bboxWidthPx": _bbox_width(self.selected_bbox),
            "bboxHeightPx": _bbox_height(self.selected_bbox),
            "interocularDistancePx": self.interocular_distance_px,
            "faceCenter": (
                {"x": self.face_center_x, "y": self.face_center_y}
                if self.face_center_x is not None and self.face_center_y is not None
                else None
            ),
            "yawDeg": _selected_measurement(self.detected_faces, "yawDeg"),
            "pitchDeg": _selected_measurement(self.detected_faces, "pitchDeg"),
            "rollDeg": _selected_measurement(self.detected_faces, "rollDeg"),
            "borderClipped": self.border_clipped,
            "faceBboxIntersectsEditableMask": self.face_bbox_intersects_editable_mask,
            "faceBboxMaskOverlapAreaPx": self.face_bbox_mask_overlap_area_px,
            "faceBboxMaskOverlapRatio": self.face_bbox_mask_overlap_ratio,
            "editableMaskNonzeroPixelCount": self.editable_mask_nonzero_pixel_count,
            "editableMaskCoverageRatio": self.editable_mask_coverage_ratio,
            "faceCenterInsideEditableMask": self.face_center_inside_editable_mask,
            "status": self.status,
            "qualityTier": self.quality_tier,
            "failureReasons": list(self.failure_reasons),
            "measurementSha256": self.measurement_sha256,
        }


class FaceObservabilityService:
    """CPU-only observation service with no route or quality decision logic."""

    schema_version = "1.0"

    def __init__(self, detector: FaceDetector, config: FaceObservabilityConfig) -> None:
        self._validate_config(config)
        for attribute, expected in (
            ("detector_id", config.detector_id),
            ("detector_version", config.detector_version),
            ("detector_config_sha256", config.detector_config_sha256),
        ):
            actual = getattr(detector, attribute, None)
            if actual is not None and actual != expected:
                raise FaceObservabilityError(f"detector/config mismatch: {attribute}")
        self._detector = detector
        self._config = config

    def observe(self, image_bytes: bytes, editable_mask: bytes) -> FaceObservability:
        image_sha256 = _sha256_bytes(image_bytes)
        mask_sha256 = _sha256_bytes(editable_mask)
        try:
            image = _decode_image(image_bytes)
        except Exception:
            return self._invalid(
                image_sha256=image_sha256,
                mask_sha256=mask_sha256,
                reason="MALFORMED_IMAGE",
            )

        try:
            mask = _decode_mask(editable_mask)
        except Exception:
            return self._invalid(
                image_sha256=image_sha256,
                image_size=image.size,
                mask_sha256=mask_sha256,
                reason="INVALID_MASK",
            )
        if mask.size != image.size:
            return self._invalid(
                image_sha256=image_sha256,
                image_size=image.size,
                mask_sha256=mask_sha256,
                mask_size=mask.size,
                reason="MASK_DIMENSIONS_MISMATCH",
            )

        try:
            detections = tuple(self._detector.detect(image.copy()))
        except Exception:
            return self._invalid(
                image_sha256=image_sha256,
                image_size=image.size,
                mask_sha256=mask_sha256,
                mask_size=mask.size,
                reason="DETECTOR_FAILURE",
            )

        normalized, detection_failures = self._normalize_detections(detections, image.size)
        mask_array = np.asarray(mask, dtype=np.uint8)
        mask_nonzero = int(np.count_nonzero(mask_array))
        common = {
            "image_sha256": image_sha256,
            "image_size": image.size,
            "mask_sha256": mask_sha256,
            "mask_size": mask.size,
            "face_count": len(detections),
            "detected_faces": tuple(normalized),
            "mask_nonzero": mask_nonzero,
            "mask_coverage": mask_nonzero / float(image.width * image.height),
        }

        if detection_failures:
            return self._build(**common, reasons=detection_failures, status="INVALID", tier="UNRECOVERABLE")
        if not normalized:
            return self._build(
                **common,
                reasons=("NO_FACE_DETECTED",),
                status="INVALID",
                tier="UNRECOVERABLE",
            )
        if len(normalized) > 1:
            return self._build(
                **common,
                reasons=("MULTIPLE_FACES_DETECTED",),
                status="AMBIGUOUS",
                tier="LIMITED",
            )

        selected = normalized[0]
        failures: list[str] = []
        if float(selected["confidence"]) < self._config.minimum_confidence:
            failures.append("WEAK_DETECTION")
        metrics = _mask_metrics(selected["bbox"], mask_array, image.size)
        if failures:
            return self._build(
                **common,
                selected_index=0,
                selected=selected,
                metrics=metrics,
                reasons=tuple(failures),
                status="INVALID",
                tier="LIMITED",
            )
        return self._build(
            **common,
            selected_index=0,
            selected=selected,
            metrics=metrics,
            reasons=(),
            status="VALID",
            tier="HIGH",
        )

    def _normalize_detections(
        self,
        detections: tuple[FaceDetection, ...],
        image_size: tuple[int, int],
    ) -> tuple[tuple[dict[str, Any], ...], tuple[str, ...]]:
        width, height = image_size
        normalized: list[dict[str, Any]] = []
        failures: list[str] = []
        for detection in detections:
            try:
                if not isinstance(detection, FaceDetection):
                    raise ValueError("detector output is not FaceDetection")
                confidence = float(detection.confidence)
                bbox = tuple(float(value) for value in detection.bbox)
                landmarks = tuple((float(x), float(y)) for x, y in detection.landmarks)
                optional = {
                    "yawDeg": _finite_optional(detection.yaw_deg),
                    "pitchDeg": _finite_optional(detection.pitch_deg),
                    "rollDeg": _finite_optional(detection.roll_deg),
                }
                if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
                    raise ValueError("confidence")
                if len(bbox) != 4 or not all(math.isfinite(value) for value in bbox):
                    raise ValueError("bbox")
                left, top, right, bottom = bbox
                if left < 0 or top < 0 or right <= left or bottom <= top or right > width or bottom > height:
                    failures.append("INVALID_BBOX")
                    continue
                if len(landmarks) != 5 or any(
                    not math.isfinite(x) or not math.isfinite(y) or x < 0 or y < 0 or x > width or y > height
                    for x, y in landmarks
                ):
                    failures.append("INVALID_LANDMARKS")
                    continue
                normalized.append({
                    "confidence": confidence,
                    "bbox": bbox,
                    "landmarks": landmarks,
                    **optional,
                })
            except (TypeError, ValueError, OverflowError):
                failures.append("INVALID_MEASUREMENTS")

        normalized.sort(key=lambda item: (*item["bbox"], item["confidence"]))
        return tuple(normalized), tuple(dict.fromkeys(failures))

    def _build(
        self,
        *,
        image_sha256: str,
        image_size: tuple[int, int],
        mask_sha256: str,
        mask_size: tuple[int, int],
        face_count: int,
        detected_faces: tuple[dict[str, Any], ...],
        mask_nonzero: int,
        mask_coverage: float,
        reasons: tuple[str, ...],
        status: str,
        tier: str,
        selected_index: int | None = None,
        selected: dict[str, Any] | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> FaceObservability:
        selected_bbox = selected["bbox"] if selected else None
        selected_landmarks = selected["landmarks"] if selected else ()
        payload = {
            "schemaVersion": self.schema_version,
            "imageSha256": image_sha256,
            "imageWidth": image_size[0],
            "imageHeight": image_size[1],
            "maskSha256": mask_sha256,
            "maskWidth": mask_size[0],
            "maskHeight": mask_size[1],
            "detectorId": self._config.detector_id,
            "detectorVersion": self._config.detector_version,
            "detectorConfigSha256": self._config.detector_config_sha256,
            "measurementConfigSha256": self._config.measurement_config_sha256,
            "faceCount": face_count,
            "selectedFaceIndex": selected_index,
            "selectedFaceConfidence": selected["confidence"] if selected else None,
            "bbox": _bbox_dict(selected_bbox),
            "landmarks": _landmark_dicts(selected_landmarks),
            "detectedFaces": [_json_detection(item) for item in detected_faces],
            "bboxWidthPx": _bbox_width(selected_bbox),
            "bboxHeightPx": _bbox_height(selected_bbox),
            "interocularDistancePx": _interocular(selected_landmarks),
            "faceCenter": _face_center(selected_bbox),
            "yawDeg": selected.get("yawDeg") if selected else None,
            "pitchDeg": selected.get("pitchDeg") if selected else None,
            "rollDeg": selected.get("rollDeg") if selected else None,
            "borderClipped": _border_clipped(selected_bbox, image_size),
            "faceBboxIntersectsEditableMask": metrics.get("intersects") if metrics else None,
            "faceBboxMaskOverlapAreaPx": metrics.get("overlap_area") if metrics else None,
            "faceBboxMaskOverlapRatio": metrics.get("overlap_ratio") if metrics else None,
            "editableMaskNonzeroPixelCount": mask_nonzero,
            "editableMaskCoverageRatio": mask_coverage,
            "faceCenterInsideEditableMask": metrics.get("center_inside") if metrics else None,
            "status": status,
            "qualityTier": tier,
            "failureReasons": list(reasons),
        }
        measurement_sha256 = _sha256_canonical(payload)
        return FaceObservability(
            schema_version=self.schema_version,
            image_sha256=image_sha256,
            image_width=image_size[0],
            image_height=image_size[1],
            mask_sha256=mask_sha256,
            mask_width=mask_size[0],
            mask_height=mask_size[1],
            detector_id=self._config.detector_id,
            detector_version=self._config.detector_version,
            detector_config_sha256=self._config.detector_config_sha256,
            measurement_config_sha256=self._config.measurement_config_sha256,
            face_count=face_count,
            selected_face_index=selected_index,
            selected_face_confidence=selected["confidence"] if selected else None,
            selected_bbox=selected_bbox,
            selected_landmarks=selected_landmarks,
            detected_faces=tuple(_immutable_detection(item) for item in detected_faces),
            interocular_distance_px=_interocular(selected_landmarks),
            face_center_x=_face_center(selected_bbox)["x"] if _face_center(selected_bbox) else None,
            face_center_y=_face_center(selected_bbox)["y"] if _face_center(selected_bbox) else None,
            border_clipped=_border_clipped(selected_bbox, image_size),
            face_bbox_intersects_editable_mask=metrics.get("intersects") if metrics else None,
            face_bbox_mask_overlap_area_px=metrics.get("overlap_area") if metrics else None,
            face_bbox_mask_overlap_ratio=metrics.get("overlap_ratio") if metrics else None,
            editable_mask_nonzero_pixel_count=mask_nonzero,
            editable_mask_coverage_ratio=mask_coverage,
            face_center_inside_editable_mask=metrics.get("center_inside") if metrics else None,
            status=status,
            quality_tier=tier,
            failure_reasons=reasons,
            measurement_sha256=measurement_sha256,
        )

    def _invalid(
        self,
        *,
        image_sha256: str,
        reason: str,
        image_size: tuple[int, int] = (0, 0),
        mask_sha256: str = "",
        mask_size: tuple[int, int] = (0, 0),
    ) -> FaceObservability:
        return self._build(
            image_sha256=image_sha256,
            image_size=image_size,
            mask_sha256=mask_sha256,
            mask_size=mask_size,
            face_count=0,
            detected_faces=(),
            mask_nonzero=0,
            mask_coverage=0.0,
            reasons=(reason,),
            status="INVALID",
            tier="UNRECOVERABLE",
        )

    @staticmethod
    def _validate_config(config: FaceObservabilityConfig) -> None:
        for value in (config.detector_id, config.detector_version, config.detector_config_sha256,
                      config.measurement_config_sha256):
            if not isinstance(value, str) or not value:
                raise FaceObservabilityError("detector/config is not pinned")
        if not _is_sha256(config.detector_config_sha256) or not _is_sha256(config.measurement_config_sha256):
            raise FaceObservabilityError("detector/config hash is invalid")
        if not math.isfinite(config.minimum_confidence) or not 0.0 <= config.minimum_confidence <= 1.0:
            raise FaceObservabilityError("detector confidence configuration is invalid")


def _decode_image(data: bytes) -> Image.Image:
    if not isinstance(data, bytes) or not data:
        raise FaceObservabilityError("image bytes are empty")
    with Image.open(BytesIO(data)) as source:
        source.load()
        image = ImageOps.exif_transpose(source).convert("RGB")
    if image.width <= 0 or image.height <= 0:
        raise FaceObservabilityError("image dimensions are invalid")
    return image


def _decode_mask(data: bytes) -> Image.Image:
    if not isinstance(data, bytes) or not data:
        raise FaceObservabilityError("mask bytes are empty")
    with Image.open(BytesIO(data)) as source:
        source.load()
        if source.mode not in {"1", "L", "I", "I;16", "F"}:
            raise FaceObservabilityError("editable mask must be grayscale")
        mask = source.copy().convert("L")
    if mask.width <= 0 or mask.height <= 0:
        raise FaceObservabilityError("mask dimensions are invalid")
    return mask


def _mask_metrics(
    bbox: tuple[float, float, float, float],
    mask: np.ndarray,
    image_size: tuple[int, int],
) -> dict[str, Any]:
    left, top, right, bottom = bbox
    width, height = image_size
    x0, y0 = max(0, math.floor(left)), max(0, math.floor(top))
    x1, y1 = min(width, math.ceil(right)), min(height, math.ceil(bottom))
    overlap_area = int(np.count_nonzero(mask[y0:y1, x0:x1])) if x1 > x0 and y1 > y0 else 0
    bbox_area = max(0.0, (right - left) * (bottom - top))
    center_x, center_y = (left + right) / 2.0, (top + bottom) / 2.0
    cx, cy = math.floor(center_x), math.floor(center_y)
    center_inside = bool(0 <= cx < width and 0 <= cy < height and mask[cy, cx] > 0)
    return {
        "intersects": overlap_area > 0,
        "overlap_area": overlap_area,
        "overlap_ratio": overlap_area / bbox_area if bbox_area else 0.0,
        "center_inside": center_inside,
    }


def _json_detection(item: Mapping[str, Any]) -> dict[str, Any]:
    bbox = item["bbox"]
    landmarks = item["landmarks"]
    return {
        "confidence": item["confidence"],
        "bbox": dict(bbox) if isinstance(bbox, Mapping) else _bbox_dict(bbox),
        "landmarks": [
            dict(landmark) if isinstance(landmark, Mapping) else {"x": landmark[0], "y": landmark[1]}
            for landmark in landmarks
        ],
        "yawDeg": item.get("yawDeg"),
        "pitchDeg": item.get("pitchDeg"),
        "rollDeg": item.get("rollDeg"),
    }


def _immutable_detection(item: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType({
        "confidence": item["confidence"],
        "bbox": MappingProxyType(_bbox_dict(item["bbox"]) or {}),
        "landmarks": tuple(
            MappingProxyType({"x": x, "y": y}) for x, y in item["landmarks"]
        ),
        "yawDeg": item.get("yawDeg"),
        "pitchDeg": item.get("pitchDeg"),
        "rollDeg": item.get("rollDeg"),
    })


def _bbox_dict(bbox: tuple[float, float, float, float] | None) -> dict[str, float] | None:
    if bbox is None:
        return None
    return {"left": bbox[0], "top": bbox[1], "right": bbox[2], "bottom": bbox[3]}


def _landmark_dicts(landmarks: tuple[tuple[float, float], ...]) -> list[dict[str, float]]:
    return [{"x": x, "y": y} for x, y in landmarks]


def _bbox_width(bbox: tuple[float, float, float, float] | None) -> float | None:
    return bbox[2] - bbox[0] if bbox else None


def _bbox_height(bbox: tuple[float, float, float, float] | None) -> float | None:
    return bbox[3] - bbox[1] if bbox else None


def _face_center(bbox: tuple[float, float, float, float] | None) -> dict[str, float] | None:
    if bbox is None:
        return None
    return {"x": (bbox[0] + bbox[2]) / 2.0, "y": (bbox[1] + bbox[3]) / 2.0}


def _interocular(landmarks: tuple[tuple[float, float], ...]) -> float | None:
    if len(landmarks) != 5:
        return None
    return math.hypot(landmarks[1][0] - landmarks[0][0], landmarks[1][1] - landmarks[0][1])


def _border_clipped(bbox: tuple[float, float, float, float] | None, image_size: tuple[int, int]) -> bool | None:
    if bbox is None:
        return None
    return bbox[0] <= 0 or bbox[1] <= 0 or bbox[2] >= image_size[0] or bbox[3] >= image_size[1]


def _selected_measurement(faces: tuple[dict[str, Any], ...], key: str) -> float | None:
    if len(faces) != 1:
        return None
    return faces[0].get(key)


def _finite_optional(value: float | None) -> float | None:
    if value is None:
        return None
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError("non-finite optional measurement")
    return converted


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_canonical(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()
    return _sha256_bytes(encoded)


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdef" for char in value)


MEASUREMENT_CONFIG = {
    "version": "face-observability-measurement-v1",
    "decode": "exif_transpose_then_rgb",
    "landmarks": "five_point_existing_detector_order",
    "mask": "editable_luminance_greater_than_zero",
    "geometry": "bbox_area_intersection_and_center_point",
    "finite_values": "reject_non_finite",
}
MEASUREMENT_CONFIG_SHA256 = _sha256_canonical(MEASUREMENT_CONFIG)
