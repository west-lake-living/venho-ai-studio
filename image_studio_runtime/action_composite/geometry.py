from __future__ import annotations

import math
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional, Protocol

from PIL import Image

from .models import BoundingBox, FaceGeometry


class FaceDetector(Protocol):
    def detect(self, image: Image.Image, requested_bbox: Optional[BoundingBox] = None) -> FaceGeometry: ...


class BBoxFaceDetector:
    """Deterministic detector adapter for POC and external detector handoff.

    Production detectors can implement the same protocol. A bbox is mandatory
    unless the image manifest provides ``face_bbox``; this prevents silently
    repairing the wrong region.
    """

    def detect(self, image: Image.Image, requested_bbox: Optional[BoundingBox] = None) -> FaceGeometry:
        bbox = requested_bbox
        if bbox is None:
            raise ValueError("face_bbox is required until a production detector adapter is configured")
        if bbox.right > image.width or bbox.bottom > image.height:
            raise ValueError("face_bbox is outside base image bounds")
        return FaceGeometry(face_bbox=bbox, head_bbox=bbox.padded(0.55, image.width, image.height),
                            face_scale=bbox.width / image.width)


class FaceGeometryEvidenceBlocked(RuntimeError):
    """Raised when real observed-face evidence cannot be obtained.

    This is intentionally distinct from the deterministic ``BBoxFaceDetector``:
    a supplied crop rectangle is valid expected geometry, but is not evidence
    about the restored artifact.
    """


class InsightFaceGeometryExtractor:
    """Extract observed geometry from the finished artifact with InsightFace.

    ``buffalo_l`` produces a detected face box and five facial landmarks.  The
    landmark set is converted to a PnP pose, so yaw/pitch/roll are observations
    of the image being audited rather than values copied from the input lock.
    No face, multiple faces, or a missing runtime blocks the execution.
    """

    method_version = "insightface-buffalo-l-pnp-preprocess-v3"
    landmark_order = ("left_eye", "right_eye", "nose", "left_mouth_corner", "right_mouth_corner")
    pnp_initial_method = "cv2.SOLVEPNP_SQPNP"
    pnp_refinement_method = "cv2.SOLVEPNP_ITERATIVE(useExtrinsicGuess=True)"
    preprocessing_version = "insightface-analysis-upscale-cubic-v1"
    minimum_analysis_side = 1024

    def __init__(self, *, model_name: str = "buffalo_l", det_size: tuple[int, int] = (1024, 1024),
                 analyzer: Any | None = None, cv2_module: Any | None = None) -> None:
        self.model_name = model_name
        self.det_size = det_size
        self._analyzer = analyzer
        self._cv2 = cv2_module
        self.last_provenance: dict[str, Any] | None = None

    def __call__(self, artifact_path: Path) -> FaceGeometry:
        return self.extract(artifact_path)

    def extract(self, artifact_path: str | Path) -> FaceGeometry:
        path = Path(artifact_path)
        if not path.is_file():
            raise FaceGeometryEvidenceBlocked(f"Observed geometry artifact is missing: {path}")
        analyzer, cv2 = self._runtime()
        try:
            import numpy as np
            image = np.asarray(Image.open(path).convert("RGB"))
            analysis_image, scale_factor = self._analysis_image(image, cv2)
            faces = list(analyzer.get(analysis_image))
        except FaceGeometryEvidenceBlocked:
            raise
        except Exception as exc:  # pragma: no cover - provider-dependent details
            raise FaceGeometryEvidenceBlocked(f"InsightFace geometry extraction failed: {exc}") from exc
        if len(faces) != 1:
            raise FaceGeometryEvidenceBlocked(
                f"InsightFace geometry extraction requires exactly one face; detected {len(faces)}"
            )
        face = faces[0]
        bbox = getattr(face, "bbox", None)
        landmarks = getattr(face, "kps", None)
        if bbox is None or landmarks is None or len(landmarks) != 5:
            raise FaceGeometryEvidenceBlocked("InsightFace result lacks one face bbox or five landmarks")
        original_bbox = self._map_to_original(bbox, scale_factor)
        original_landmarks = self._map_to_original(landmarks, scale_factor)
        self.last_provenance = {
            "original_artifact": str(path),
            "original_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "original_dimensions": {"width": int(image.shape[1]), "height": int(image.shape[0])},
            "analysis_dimensions": {"width": int(analysis_image.shape[1]), "height": int(analysis_image.shape[0])},
            "scale_factor": scale_factor,
            "preprocessing_method": self.preprocessing_version,
            "detector": "InsightFace.FaceAnalysis",
            "model": self.model_name,
            "detection_score": float(getattr(face, "det_score", 0.0)),
            "landmark_count": 5,
            "landmark_order": list(self.landmark_order),
            "landmarks": [[float(point[0]), float(point[1])] for point in original_landmarks],
        }
        return self._to_geometry(original_bbox, original_landmarks,
                                 image_width=image.shape[1], image_height=image.shape[0], cv2=cv2,
                                 provenance=self.last_provenance)

    def _analysis_image(self, image: Any, cv2: Any) -> tuple[Any, float]:
        """Upscale only the in-memory detector input, retaining source coordinates."""
        shortest_side = min(image.shape[0], image.shape[1])
        if shortest_side >= self.minimum_analysis_side:
            return image, 1.0
        scale_factor = self.minimum_analysis_side / float(shortest_side)
        width = int(round(image.shape[1] * scale_factor))
        height = int(round(image.shape[0] * scale_factor))
        return cv2.resize(image, (width, height), interpolation=cv2.INTER_CUBIC), scale_factor

    @staticmethod
    def _map_to_original(coordinates: Any, scale_factor: float) -> Any:
        import numpy as np

        return np.asarray(coordinates, dtype="float64") / scale_factor

    def _runtime(self) -> tuple[Any, Any]:
        if self._analyzer is not None and self._cv2 is not None:
            return self._analyzer, self._cv2
        try:
            import cv2
            from insightface.app import FaceAnalysis
        except ImportError as exc:
            raise FaceGeometryEvidenceBlocked(
                "InsightFace geometry runtime is unavailable; install venho-ai-studio[geometry]"
            ) from exc
        if self._analyzer is None:
            try:
                analyzer = FaceAnalysis(name=self.model_name, providers=["CPUExecutionProvider"])
                analyzer.prepare(ctx_id=-1, det_size=self.det_size)
                self._analyzer = analyzer
            except Exception as exc:  # pragma: no cover - model/runtime dependent
                raise FaceGeometryEvidenceBlocked(f"InsightFace geometry runtime initialization failed: {exc}") from exc
        self._cv2 = cv2
        return self._analyzer, self._cv2

    @staticmethod
    def _to_geometry(bbox: Any, landmarks: Any, *, image_width: int, image_height: int,
                     cv2: Any, provenance: dict[str, Any] | None = None) -> FaceGeometry:
        import numpy as np

        try:
            left, top, right, bottom = (int(round(float(value))) for value in bbox[:4])
            face_bbox = BoundingBox(left=max(0, left), top=max(0, top),
                                    right=min(image_width, right), bottom=min(image_height, bottom))
            points = np.asarray(landmarks, dtype="float64")
            if points.shape != (5, 2):
                raise ValueError("expected 5x2 landmarks")
            # Canonical 3-D coordinates match InsightFace's documented five-point
            # order: left eye, right eye, nose, left mouth, right mouth.
            object_points = np.asarray([
                (-30.0, 35.0, -30.0), (30.0, 35.0, -30.0), (0.0, 0.0, 0.0),
                (-25.0, -35.0, -20.0), (25.0, -35.0, -20.0),
            ], dtype="float64")
            focal = float(max(image_width, image_height))
            camera = np.asarray([[focal, 0.0, image_width / 2],
                                 [0.0, focal, image_height / 2],
                                 [0.0, 0.0, 1.0]], dtype="float64")
            if not hasattr(cv2, "SOLVEPNP_SQPNP"):
                raise ValueError("OpenCV runtime does not provide SOLVEPNP_SQPNP for five landmarks")
            distortion = np.zeros((4, 1), dtype="float64")
            ok, rotation_vector, translation = cv2.solvePnP(
                object_points, points, camera, distortion, flags=cv2.SOLVEPNP_SQPNP
            )
            if not ok or rotation_vector is None or translation is None:
                raise ValueError("SQPNP returned false")
            initial_rvec = np.asarray(rotation_vector, dtype="float64")
            initial_tvec = np.asarray(translation, dtype="float64")
            refinement_used = False
            if hasattr(cv2, "SOLVEPNP_ITERATIVE"):
                refined_ok, refined_rvec, refined_tvec = cv2.solvePnP(
                    object_points, points, camera, distortion,
                    rvec=initial_rvec, tvec=initial_tvec,
                    useExtrinsicGuess=True, flags=cv2.SOLVEPNP_ITERATIVE,
                )
                if refined_ok and refined_rvec is not None and refined_tvec is not None:
                    rotation_vector, translation = refined_rvec, refined_tvec
                    refinement_used = True
            rotation_vector = np.asarray(rotation_vector, dtype="float64")
            translation = np.asarray(translation, dtype="float64")
            if not np.isfinite(rotation_vector).all() or not np.isfinite(translation).all():
                raise ValueError("PnP returned NaN or Inf")
            rotation, _ = cv2.Rodrigues(rotation_vector)
            if rotation.shape != (3, 3) or not np.isfinite(rotation).all():
                raise ValueError("PnP returned an invalid rotation matrix")
            projected, _ = cv2.projectPoints(object_points, rotation_vector, translation, camera, distortion)
            projected = np.asarray(projected, dtype="float64").reshape(-1, 2)
            reprojection_error = float(np.sqrt(np.mean(np.sum((projected - points) ** 2, axis=1))))
            if not math.isfinite(reprojection_error):
                raise ValueError("PnP reprojection error is not finite")
            pitch, yaw, roll = _rotation_to_euler(rotation)
            for angle in (pitch, yaw, roll):
                if not math.isfinite(angle):
                    raise ValueError("PnP angle is not finite")
            if provenance is not None:
                provenance["pnp"] = {
                    "initial_solver": "cv2.SOLVEPNP_SQPNP",
                    "refinement_method": "cv2.SOLVEPNP_ITERATIVE(useExtrinsicGuess=True)",
                    "refinement_used": refinement_used,
                    "synthetic_landmarks_added": 0,
                    "object_point_count": int(len(object_points)),
                    "image_point_count": int(len(points)),
                    "distortion_coefficients": distortion.reshape(-1).tolist(),
                    "rvec": rotation_vector.reshape(-1).tolist(),
                    "tvec": translation.reshape(-1).tolist(),
                    "reprojection_error_px": reprojection_error,
                    "angle_convention": "rotation matrix XYZ decomposition; output pitch,yaw,roll in degrees",
                    "angle_sign_convention": "existing _rotation_to_euler convention preserved",
                    "angle_range": "atan2-derived approximately [-180,180] degrees",
                    "rotation_order": "existing _rotation_to_euler order preserved",
                    "camera_matrix": camera.tolist(),
                }
        except Exception as exc:
            raise FaceGeometryEvidenceBlocked(f"InsightFace landmark geometry is invalid: {exc}") from exc
        return FaceGeometry(
            face_bbox=face_bbox,
            head_bbox=face_bbox.padded(0.55, image_width, image_height),
            yaw=yaw,
            pitch=pitch,
            roll=roll,
            face_scale=face_bbox.width / image_width,
            eye_line=float((points[0][1] + points[1][1]) / 2),
            nose_axis=float(points[2][0]),
            mouth_line=float((points[3][1] + points[4][1]) / 2),
        )


@dataclass(frozen=True)
class FullFrameReinsertionGeometryResult:
    """Observed geometry recovered from an analysis-only reinserted frame."""

    geometry: FaceGeometry
    crop_box: BoundingBox
    original_crop_size: tuple[int, int]
    raw_restored_size: tuple[int, int]
    detection_bbox_full_frame: tuple[float, float, float, float]
    detection_score: float
    detection_count: int
    raw_restored_sha256: str
    analysis_artifact: str
    resize_method: str
    landmarks_crop_relative: tuple[tuple[float, float], ...]


class FullFrameReinsertionGeometryRecovery:
    """Recover observed geometry with the restored crop in its real scene context.

    This component is deliberately analysis-only.  It never writes the raw
    restored artifact or changes detector configuration; it writes only the
    caller-supplied derived full-frame artifact.
    """

    resize_method = "PIL.Resampling.BICUBIC"
    method_version = "full-frame-reinsertion-geometry-v1"

    def __init__(self, extractor: InsightFaceGeometryExtractor | None = None) -> None:
        self.extractor = extractor or InsightFaceGeometryExtractor()
        self.last_provenance: dict[str, Any] | None = None

    def recover(self, *, base_artifact: str | Path, raw_restored_artifact: str | Path,
                crop_box: BoundingBox | None, analysis_artifact: str | Path) -> FullFrameReinsertionGeometryResult:
        if crop_box is None:
            raise FaceGeometryEvidenceBlocked("Crop placement metadata is required for full-frame reinsertion")
        base_path = Path(base_artifact)
        raw_path = Path(raw_restored_artifact)
        if not base_path.is_file() or not raw_path.is_file():
            raise FaceGeometryEvidenceBlocked("Full-frame base or raw restored crop artifact is missing")
        raw_sha256 = hashlib.sha256(raw_path.read_bytes()).hexdigest()
        base = Image.open(base_path).convert("RGB")
        raw = Image.open(raw_path).convert("RGB")
        if crop_box.right > base.width or crop_box.bottom > base.height:
            raise FaceGeometryEvidenceBlocked("Crop placement metadata is outside the full-frame base image")
        original_size = (crop_box.width, crop_box.height)
        analysis_crop = raw.resize(original_size, Image.Resampling.BICUBIC)
        analysis = base.copy()
        analysis.paste(analysis_crop, (crop_box.left, crop_box.top))
        self._verify_only_crop_changed(base, analysis, crop_box)
        analysis_path = Path(analysis_artifact)
        analysis_path.parent.mkdir(parents=True, exist_ok=True)
        analysis.save(analysis_path, format="PNG")

        analyzer, cv2 = self.extractor._runtime()
        import numpy as np

        full_array = np.asarray(analysis)
        faces = list(analyzer.get(full_array))
        detection = None
        if faces:
            detection = {
                "bbox": [float(value) for value in faces[0].bbox[:4]],
                "score": float(getattr(faces[0], "det_score")),
            }
        self.last_provenance = {
            "crop_box_full_frame": crop_box.model_dump(),
            "original_crop_size": {"width": original_size[0], "height": original_size[1]},
            "raw_restored_size": {"width": raw.width, "height": raw.height},
            "analysis_artifact": str(analysis_path),
            "resize_method": self.resize_method,
            "detection_count": len(faces),
            "detection": detection,
            "raw_restored_sha256": raw_sha256,
        }
        if len(faces) != 1:
            raise FaceGeometryEvidenceBlocked(
                f"Full-frame reinsertion geometry requires exactly one face; detected {len(faces)}"
            )
        face = faces[0]
        bbox = getattr(face, "bbox", None)
        landmarks = getattr(face, "kps", None)
        if bbox is None or landmarks is None or len(landmarks) != 5:
            raise FaceGeometryEvidenceBlocked("InsightFace result lacks one face bbox or five landmarks")
        full_geometry = self.extractor._to_geometry(bbox, landmarks, image_width=base.width,
                                                    image_height=base.height, cv2=cv2)
        crop_geometry, crop_landmarks = self._remap_to_crop(
            bbox=bbox, landmarks=landmarks, crop_box=crop_box, crop_width=original_size[0],
            crop_height=original_size[1], full_geometry=full_geometry,
        )
        return FullFrameReinsertionGeometryResult(
            geometry=crop_geometry,
            crop_box=crop_box,
            original_crop_size=original_size,
            raw_restored_size=(raw.width, raw.height),
            detection_bbox_full_frame=tuple(float(value) for value in bbox[:4]),
            detection_score=float(getattr(face, "det_score")),
            detection_count=len(faces),
            raw_restored_sha256=raw_sha256,
            analysis_artifact=str(analysis_path),
            resize_method=self.resize_method,
            landmarks_crop_relative=crop_landmarks,
        )

    @staticmethod
    def _verify_only_crop_changed(base: Image.Image, analysis: Image.Image, crop_box: BoundingBox) -> None:
        import numpy as np

        unchanged = np.asarray(base) == np.asarray(analysis)
        outside = np.ones((base.height, base.width), dtype=bool)
        outside[crop_box.top:crop_box.bottom, crop_box.left:crop_box.right] = False
        if not bool(unchanged.all(axis=2)[outside].all()):
            raise FaceGeometryEvidenceBlocked("Full-frame analysis image differs from base outside crop placement")

    @staticmethod
    def _remap_to_crop(*, bbox: Any, landmarks: Any, crop_box: BoundingBox, crop_width: int,
                       crop_height: int, full_geometry: FaceGeometry) -> tuple[FaceGeometry, tuple[tuple[float, float], ...]]:
        import numpy as np

        relative_bbox = np.asarray(bbox[:4], dtype="float64") - np.asarray(
            [crop_box.left, crop_box.top, crop_box.left, crop_box.top], dtype="float64"
        )
        left, top, right, bottom = (int(round(float(value))) for value in relative_bbox)
        if left < 0 or top < 0 or right > crop_width or bottom > crop_height or left >= right or top >= bottom:
            raise FaceGeometryEvidenceBlocked("Full-frame detected face does not lie fully within the recorded crop placement")
        face_bbox = BoundingBox(left=left, top=top, right=right, bottom=bottom)
        relative_landmarks = np.asarray(landmarks, dtype="float64") - np.asarray(
            [crop_box.left, crop_box.top], dtype="float64"
        )
        if relative_landmarks.shape != (5, 2):
            raise FaceGeometryEvidenceBlocked("InsightFace result lacks five remappable landmarks")
        points = tuple((float(point[0]), float(point[1])) for point in relative_landmarks)
        geometry = FaceGeometry(
            face_bbox=face_bbox,
            head_bbox=face_bbox.padded(0.55, crop_width, crop_height),
            yaw=full_geometry.yaw,
            pitch=full_geometry.pitch,
            roll=full_geometry.roll,
            face_scale=face_bbox.width / crop_width,
            eye_line=float((relative_landmarks[0][1] + relative_landmarks[1][1]) / 2),
            nose_axis=float(relative_landmarks[2][0]),
            mouth_line=float((relative_landmarks[3][1] + relative_landmarks[4][1]) / 2),
        )
        return geometry, points


def _rotation_to_euler(rotation: Any) -> tuple[float, float, float]:
    """Return pitch, yaw, roll in degrees from a PnP rotation matrix."""
    sy = math.sqrt(float(rotation[0, 0]) ** 2 + float(rotation[1, 0]) ** 2)
    if sy < 1e-6:
        pitch = math.atan2(-float(rotation[1, 2]), float(rotation[1, 1]))
        yaw = math.atan2(-float(rotation[2, 0]), sy)
        roll = 0.0
    else:
        pitch = math.atan2(float(rotation[2, 1]), float(rotation[2, 2]))
        yaw = math.atan2(-float(rotation[2, 0]), sy)
        roll = math.atan2(float(rotation[1, 0]), float(rotation[0, 0]))
    return tuple(math.degrees(value) for value in (pitch, yaw, roll))


def load_image(path: str | Path) -> Image.Image:
    image = Image.open(path).convert("RGBA")
    if image.width < 64 or image.height < 64:
        raise ValueError("base image is too small for face restoration")
    return image
