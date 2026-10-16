"""Local ArcFace identity similarity: pinned YuNet detection + pinned w600k_r50 embedding.

Measures how close the face in a candidate image is to approved reference faces. It only
measures; the pass/fail policy belongs to the caller. No GPU, network or provider is involved:
the ONNX model runs on CPU through ``cv2.dnn`` (bit-identical to onnxruntime for this model).

Face selection: the largest detected face is the subject. Other faces whose box area is at
least ``SECONDARY_FACE_AREA_RATIO`` of the subject's are reported as ``prominentFaceCount`` so
the caller can apply its multiple-faces rule without failing on tiny background faces.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np
from PIL import Image

from image_studio_runtime.action_composite.geometry import YuNetGeometryExtractor

from ..application.face_observability import FaceDetection
from .face_observability_yunet import PINNED_YUNET_CONFIG_SHA256

SCHEMA = "identity-similarity-v1"
MODEL_NAME = "w600k_r50.onnx"
MODEL_SHA256 = "4c06341c33c2ca1f86781dab0e829f88ad5b64be9fba56e56bc9ebdefc619e43"
MODEL_ID = "insightface-buffalo_l-w600k_r50"
ALIGNMENT_VERSION = "arcface-5pt-similarity-112-v1"
SECONDARY_FACE_AREA_RATIO = 0.10
# Canonical ArcFace 112x112 positions for left eye, right eye, nose, mouth corners.
ARCFACE_TEMPLATE = np.array(
    [[38.2946, 51.6963], [73.5318, 51.5014], [56.0252, 71.7366],
     [41.5493, 92.3655], [70.7299, 92.2041]],
    dtype=np.float32,
)


class IdentitySimilarityBlocked(ValueError):
    """The measurement could not be made (missing model, no face in a reference, ...)."""


class FaceDetector(Protocol):
    def detect(self, image: Image.Image) -> tuple[FaceDetection, ...]: ...


class FaceEmbedder(Protocol):
    def embed(self, aligned_bgr: np.ndarray) -> np.ndarray: ...


@dataclass(frozen=True)
class ReferenceImage:
    role: str
    path: Path


def _default_model_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    return root / "models" / "identity" / "arcface_w600k_r50" / MODEL_NAME


class PinnedYuNetLandmarks:
    """The repository's pinned YuNet model and thresholds, returning boxes + five landmarks only.

    ``YuNetFaceDetector`` also solves a PnP head pose for every detection, which raises on tiny
    background faces; identity similarity needs only the landmarks for alignment.
    """

    def __init__(self, *, model_path: str | Path | None = None) -> None:
        root = Path(__file__).resolve().parents[2]
        self.model_path = Path(model_path) if model_path is not None else (
            root / "models" / "geometry" / "yunet" / YuNetGeometryExtractor.model_name
        )
        self._detector: Any | None = None

    def detect(self, image: Image.Image) -> tuple[FaceDetection, ...]:
        import cv2

        detector = self._runtime(cv2)
        rgb = np.asarray(image.convert("RGB"))
        detector.setInputSize((int(rgb.shape[1]), int(rgb.shape[0])))
        _, rows = detector.detect(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        if rows is None:
            return ()
        faces = []
        for row in rows:
            x, y, w, h = (float(v) for v in row[:4])
            landmarks = tuple((float(row[i]), float(row[i + 1])) for i in range(4, 14, 2))
            faces.append(FaceDetection(confidence=float(row[14]), bbox=(x, y, x + w, y + h),
                                       landmarks=landmarks))
        return tuple(faces)

    def _runtime(self, cv2: Any) -> Any:
        if self._detector is not None:
            return self._detector
        if not self.model_path.is_file():
            raise IdentitySimilarityBlocked(f"YuNet model artifact is missing: {self.model_path}")
        actual = hashlib.sha256(self.model_path.read_bytes()).hexdigest()
        if actual != YuNetGeometryExtractor.model_sha256:
            raise IdentitySimilarityBlocked(f"YuNet model SHA-256 mismatch: got {actual}")
        self._detector = cv2.FaceDetectorYN.create(
            str(self.model_path), "", YuNetGeometryExtractor.detector_input_size,
            YuNetGeometryExtractor.confidence_threshold, YuNetGeometryExtractor.nms_threshold,
        )
        return self._detector


class ArcFaceEmbedder:
    """CPU ``cv2.dnn`` runner for the pinned ArcFace model; verifies the model hash first."""

    def __init__(self, *, model_path: str | Path | None = None,
                 expected_model_sha256: str = MODEL_SHA256) -> None:
        self.model_path = Path(model_path) if model_path is not None else _default_model_path()
        self.expected_model_sha256 = expected_model_sha256
        self._net: Any | None = None
        self._cv2: Any | None = None

    def embed(self, aligned_bgr: np.ndarray) -> np.ndarray:
        cv2, net = self._runtime()
        blob = cv2.dnn.blobFromImage(
            aligned_bgr, 1.0 / 127.5, (112, 112), (127.5, 127.5, 127.5), swapRB=True
        )
        net.setInput(blob)
        vector = np.asarray(net.forward()[0], dtype=np.float64)
        norm = float(np.linalg.norm(vector))
        if not np.isfinite(norm) or norm == 0.0:
            raise IdentitySimilarityBlocked("ArcFace returned a degenerate embedding")
        return vector / norm

    def _runtime(self) -> tuple[Any, Any]:
        if self._net is not None:
            return self._cv2, self._net
        if not self.model_path.is_file():
            raise IdentitySimilarityBlocked(f"ArcFace model artifact is missing: {self.model_path}")
        actual = hashlib.sha256(self.model_path.read_bytes()).hexdigest()
        if actual != self.expected_model_sha256:
            raise IdentitySimilarityBlocked(
                f"ArcFace model SHA-256 mismatch: expected {self.expected_model_sha256}, got {actual}"
            )
        try:
            import cv2
        except ImportError as exc:
            raise IdentitySimilarityBlocked("OpenCV CPU runtime is unavailable") from exc
        self._cv2 = cv2
        self._net = cv2.dnn.readNetFromONNX(str(self.model_path))
        return self._cv2, self._net


def align_face(image_bgr: np.ndarray, landmarks: Sequence[Sequence[float]]) -> np.ndarray:
    import cv2

    points = np.asarray(landmarks, dtype=np.float32).reshape(5, 2)
    matrix, _ = cv2.estimateAffinePartial2D(points, ARCFACE_TEMPLATE, method=cv2.LMEDS)
    if matrix is None:
        raise IdentitySimilarityBlocked("face landmarks cannot be aligned")
    return cv2.warpAffine(image_bgr, matrix, (112, 112), borderValue=0)


def _area(face: FaceDetection) -> float:
    x0, y0, x1, y1 = face.bbox
    return max(0.0, x1 - x0) * max(0.0, y1 - y0)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _subject(
    path: Path, detector: FaceDetector
) -> tuple[np.ndarray, FaceDetection | None, int, int]:
    try:
        image = Image.open(path).convert("RGB")
    except OSError as exc:
        raise IdentitySimilarityBlocked(f"image is unreadable: {path}") from exc
    faces = detector.detect(image)
    bgr = np.ascontiguousarray(np.asarray(image)[:, :, ::-1])
    if not faces:
        return bgr, None, 0, 0
    subject = max(faces, key=_area)
    prominent = sum(1 for face in faces if _area(face) >= SECONDARY_FACE_AREA_RATIO * _area(subject))
    return bgr, subject, len(faces), prominent


def measure_identity_similarity(
    image_path: Path,
    references: Sequence[ReferenceImage],
    *,
    detector: FaceDetector | None = None,
    embedder: FaceEmbedder | None = None,
) -> dict[str, Any]:
    """Cosine similarity of the candidate's subject face to each reference's subject face."""

    if not references:
        raise IdentitySimilarityBlocked("at least one reference image is required")
    detector = detector or PinnedYuNetLandmarks()
    embedder = embedder or ArcFaceEmbedder()

    reference_rows: list[dict[str, Any]] = []
    reference_vectors: list[np.ndarray] = []
    for ref in references:
        bgr, face, _count, _prominent = _subject(ref.path, detector)
        if face is None:
            raise IdentitySimilarityBlocked(f"reference {ref.role} has no detectable face")
        reference_vectors.append(embedder.embed(align_face(bgr, face.landmarks)))
        reference_rows.append({
            "role": ref.role, "sha256": _sha256(ref.path),
            "faceConfidence": round(float(face.confidence), 4),
        })

    bgr, face, face_count, prominent = _subject(image_path, detector)
    candidate: dict[str, Any] = {
        "sha256": _sha256(image_path),
        "faceCount": face_count,
        "prominentFaceCount": prominent,
    }
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "model": {"id": MODEL_ID, "sha256": getattr(embedder, "expected_model_sha256", None)},
        "detector": {"configSha256": PINNED_YUNET_CONFIG_SHA256},
        "alignment": ALIGNMENT_VERSION,
        "secondaryFaceAreaRatio": SECONDARY_FACE_AREA_RATIO,
        "candidate": candidate,
        "references": reference_rows,
    }
    if face is None:
        result.update({"faceDetected": False, "meanCosine": None, "maxCosine": None})
        return result

    vector = embedder.embed(align_face(bgr, face.landmarks))
    cosines = [float(vector @ ref_vector) for ref_vector in reference_vectors]
    for row, cosine in zip(reference_rows, cosines):
        row["cosine"] = round(cosine, 6)
    candidate.update({
        "faceConfidence": round(float(face.confidence), 4),
        "bbox": [round(float(v), 1) for v in face.bbox],
    })
    result.update({
        "faceDetected": True,
        "meanCosine": round(float(np.mean(cosines)), 6),
        "maxCosine": round(float(np.max(cosines)), 6),
    })
    return result

