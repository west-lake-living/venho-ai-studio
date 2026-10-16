"""Local per-frame scan of a motion clip for faceless-video temporal identity validation.

Contract ``temporal-scan-v1`` (consumed by faceless-video's TemporalFrameSourcePort adapter):
frames are sampled at a fixed rate (the last frame is always kept), written once as PNG and
measured with the pinned YuNet detector. No network, no GPU, no paid call.

Per frame: face_count, the largest face's bbox normalised to [0, 1], yaw (PnP), scale (face box
area / frame area) and blur_score (Laplacian variance of the face crop, larger = sharper).
Mouth opening, occlusion, tracking and fingerprints are not measured (reported as null).
"""

from __future__ import annotations

import hashlib
import io
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .face_observability import FaceDetection, FaceDetector

SCHEMA = "temporal-scan-v1"
DEFAULT_SAMPLE_FPS = 2.0
MAX_SAMPLED_FRAMES = 120


@dataclass(frozen=True)
class DecodedFrame:
    index: int
    timestamp_ms: int
    image: Image.Image


FrameReader = Callable[[Path, float], Iterable[DecodedFrame]]


def cv2_frame_reader(video: Path, sample_fps: float) -> Iterator[DecodedFrame]:
    """Decode with OpenCV's bundled backend (the server has no ffmpeg binary)."""

    import cv2

    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise ValueError(f"video cannot be opened: {video}")
    try:
        source_fps = float(capture.get(cv2.CAP_PROP_FPS)) or 0.0
        total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if source_fps <= 0 or total <= 0:
            raise ValueError("video reports no frame rate or frame count")
        wanted = sample_indices(total, source_fps, sample_fps)
        index = 0
        while index <= wanted[-1]:
            if not capture.grab():
                break
            if index in wanted:
                ok, bgr = capture.retrieve()
                if not ok:
                    raise ValueError(f"frame {index} could not be decoded")
                yield DecodedFrame(
                    index=index,
                    timestamp_ms=round(index * 1000 / source_fps),
                    image=Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)),
                )
            index += 1
    finally:
        capture.release()


def sample_indices(total: int, source_fps: float, sample_fps: float) -> list[int]:
    if total <= 0 or source_fps <= 0 or sample_fps <= 0:
        raise ValueError("frame count, source fps and sample fps must be positive")
    step = max(1, round(source_fps / sample_fps))
    indices = list(range(0, total, step))
    if indices[-1] != total - 1:
        indices.append(total - 1)  # the last frame is a mandatory critical frame
    if len(indices) > MAX_SAMPLED_FRAMES:
        raise ValueError(f"clip would yield {len(indices)} frames > {MAX_SAMPLED_FRAMES}")
    return indices


def _png(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="PNG", optimize=False)
    return buffer.getvalue()


def _face_blur(image: Image.Image, bbox: tuple[float, float, float, float]) -> float:
    import cv2

    x1, y1, x2, y2 = (int(round(v)) for v in bbox)
    gray = np.asarray(image.convert("L"))
    crop = gray[max(0, y1) : max(0, y2), max(0, x1) : max(0, x2)]
    if crop.size == 0:
        return 0.0
    return float(cv2.Laplacian(crop, cv2.CV_64F, ksize=3).var())


def _measure(
    image: Image.Image,
    detections: tuple[FaceDetection, ...],
    blur: Callable[[Image.Image, tuple[float, float, float, float]], float],
) -> dict[str, Any]:
    width, height = image.size
    if not detections:
        return {"face_count": 0, "bbox": None, "yaw_deg": None, "scale": None, "blur_score": None}
    subject = max(detections, key=lambda d: (d.bbox[2] - d.bbox[0]) * (d.bbox[3] - d.bbox[1]))
    x1, y1, x2, y2 = subject.bbox
    return {
        "face_count": len(detections),
        "bbox": [
            round(min(max(x1 / width, 0.0), 1.0), 6),
            round(min(max(y1 / height, 0.0), 1.0), 6),
            round(min(max(x2 / width, 0.0), 1.0), 6),
            round(min(max(y2 / height, 0.0), 1.0), 6),
        ],
        "yaw_deg": None if subject.yaw_deg is None else round(float(subject.yaw_deg), 3),
        "scale": round(max(0.0, (x2 - x1) * (y2 - y1)) / (width * height), 6),
        "blur_score": round(blur(image, subject.bbox), 3),
    }


def scan_video(
    video: Path,
    out_dir: Path,
    *,
    detector: FaceDetector,
    detector_config_sha256: str,
    sample_fps: float = DEFAULT_SAMPLE_FPS,
    reader: FrameReader = cv2_frame_reader,
    blur: Callable[[Image.Image, tuple[float, float, float, float]], float] = _face_blur,
) -> dict[str, Any]:
    """Write every sampled frame once under ``out_dir`` and return the scan document."""

    if out_dir.exists() and any(out_dir.iterdir()):
        raise ValueError(f"out-dir must be empty (write-once): {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    frames: list[dict[str, Any]] = []
    for decoded in reader(video, sample_fps):
        data = _png(decoded.image)
        path = out_dir / f"frame_{decoded.timestamp_ms:08d}.png"
        path.write_bytes(data)
        frames.append({
            "timestamp_ms": decoded.timestamp_ms,
            "source_frame_index": decoded.index,
            "path": str(path),
            "sha256": hashlib.sha256(data).hexdigest(),
            "corrupt": False,
            **_measure(decoded.image, detector.detect(decoded.image), blur),
        })
    if not frames:
        raise ValueError("no frame could be decoded")
    return {
        "schema": SCHEMA,
        "video_sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
        "sample_fps": sample_fps,
        "detector_config_sha256": detector_config_sha256,
        "frames": frames,
    }
