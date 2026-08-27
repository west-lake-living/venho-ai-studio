from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from image_studio_runtime.action_composite.geometry import YuNetGeometryExtractor

from ..application.face_observability import (
    MEASUREMENT_CONFIG_SHA256,
    FaceDetection,
    FaceObservabilityConfig,
    FaceObservabilityService,
)


PINNED_YUNET_CONFIG = {
    "detectorId": "cv2.FaceDetectorYN",
    "detectorVersion": YuNetGeometryExtractor.method_version,
    "model": YuNetGeometryExtractor.model_name,
    "modelSha256": YuNetGeometryExtractor.model_sha256,
    "inputSize": list(YuNetGeometryExtractor.detector_input_size),
    "confidenceThreshold": YuNetGeometryExtractor.confidence_threshold,
    "nmsThreshold": YuNetGeometryExtractor.nms_threshold,
    "landmarkOrder": list(YuNetGeometryExtractor.landmark_order),
}
PINNED_YUNET_CONFIG_SHA256 = hashlib.sha256(
    json.dumps(PINNED_YUNET_CONFIG, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()
PINNED_YUNET_OBSERVABILITY_CONFIG = FaceObservabilityConfig(
    detector_id="cv2.FaceDetectorYN",
    detector_version=YuNetGeometryExtractor.method_version,
    detector_config_sha256=PINNED_YUNET_CONFIG_SHA256,
    measurement_config_sha256=MEASUREMENT_CONFIG_SHA256,
    minimum_confidence=YuNetGeometryExtractor.confidence_threshold,
)


class YuNetFaceDetector:
    """In-memory CPU adapter for the repository's pinned YuNet detector."""

    detector_id = PINNED_YUNET_OBSERVABILITY_CONFIG.detector_id
    detector_version = PINNED_YUNET_OBSERVABILITY_CONFIG.detector_version
    detector_config_sha256 = PINNED_YUNET_OBSERVABILITY_CONFIG.detector_config_sha256

    def __init__(
        self,
        *,
        model_path: str | Path | None = None,
        detector: Any | None = None,
        cv2_module: Any | None = None,
        expected_model_sha256: str = YuNetGeometryExtractor.model_sha256,
    ) -> None:
        root = Path(__file__).resolve().parents[3]
        self.model_path = Path(model_path) if model_path is not None else (
            root / "models" / "geometry" / "yunet" / YuNetGeometryExtractor.model_name
        )
        self.expected_model_sha256 = expected_model_sha256
        self._detector = detector
        self._cv2 = cv2_module

    def detect(self, image: Image.Image) -> tuple[FaceDetection, ...]:
        cv2 = self._runtime()
        array = np.asarray(image.convert("RGB"))
        detector_input = cv2.cvtColor(array, cv2.COLOR_RGB2BGR)
        self._detector.setInputSize((int(array.shape[1]), int(array.shape[0])))
        _, rows = self._detector.detect(detector_input)
        if rows is None:
            return ()
        detections: list[FaceDetection] = []
        for row in list(rows) if not hasattr(rows, "shape") else rows:
            values = [float(value) for value in row]
            if len(values) != 15:
                raise ValueError("YuNet detection row must contain 15 values")
            x, y, width, height = values[:4]
            landmarks = tuple((values[index], values[index + 1]) for index in range(4, 14, 2))
            bbox = (x, y, x + width, y + height)
            geometry = YuNetGeometryExtractor._to_geometry(
                bbox,
                np.asarray(landmarks, dtype="float64"),
                image_width=array.shape[1],
                image_height=array.shape[0],
                cv2=cv2,
            )
            detections.append(FaceDetection(
                confidence=values[14],
                bbox=bbox,
                landmarks=landmarks,
                yaw_deg=geometry.yaw,
                pitch_deg=geometry.pitch,
                roll_deg=geometry.roll,
            ))
        return tuple(detections)

    def _runtime(self) -> Any:
        if not self.model_path.is_file():
            raise ValueError(f"YuNet model artifact is missing: {self.model_path}")
        actual_sha256 = hashlib.sha256(self.model_path.read_bytes()).hexdigest()
        if actual_sha256 != self.expected_model_sha256:
            raise ValueError(
                f"YuNet model SHA-256 mismatch: expected {self.expected_model_sha256}, got {actual_sha256}"
            )
        if self._detector is not None and self._cv2 is not None:
            return self._cv2
        try:
            import cv2
        except ImportError as exc:
            raise ValueError("pinned YuNet CPU runtime is unavailable") from exc
        self._detector = cv2.FaceDetectorYN.create(
            str(self.model_path), "", YuNetGeometryExtractor.detector_input_size,
            YuNetGeometryExtractor.confidence_threshold, YuNetGeometryExtractor.nms_threshold,
        )
        self._cv2 = cv2
        return cv2


def create_pinned_yunet_observability_service() -> FaceObservabilityService:
    return FaceObservabilityService(
        detector=YuNetFaceDetector(),
        config=PINNED_YUNET_OBSERVABILITY_CONFIG,
    )
