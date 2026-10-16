from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

from identity_restoration.application.face_observability import FaceDetection
from identity_restoration.application.temporal_scan import (
    SCHEMA,
    DecodedFrame,
    sample_indices,
    scan_video,
)


class _Detector:
    """Two faces in the frame at t=500ms, none at t=1000ms, one otherwise."""

    def detect(self, image):  # type: ignore[no-untyped-def]
        marker = image.getpixel((0, 0))[0]
        face = FaceDetection(confidence=0.9, bbox=(10.0, 20.0, 30.0, 60.0), landmarks=(), yaw_deg=12.5)
        small = FaceDetection(confidence=0.8, bbox=(70.0, 70.0, 75.0, 75.0), landmarks=(), yaw_deg=-3.0)
        return {1: (face, small), 2: ()}.get(marker, (face,))


def _reader(video, fps):  # type: ignore[no-untyped-def]
    for index, marker in enumerate((0, 1, 2)):
        yield DecodedFrame(index=index * 12, timestamp_ms=index * 500, image=Image.new("RGB", (100, 80), (marker, 0, 0)))


def test_scan_writes_each_frame_once_and_measures_the_largest_face(tmp_path: Path) -> None:
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"clip")
    doc = scan_video(
        video, tmp_path / "frames", detector=_Detector(), detector_config_sha256="d" * 64,
        reader=_reader, blur=lambda image, bbox: 42.0,
    )
    assert doc["schema"] == SCHEMA and doc["video_sha256"] == hashlib.sha256(b"clip").hexdigest()
    first, crowded, empty = doc["frames"]
    assert first["face_count"] == 1 and first["bbox"] == [0.1, 0.25, 0.3, 0.75]
    assert first["yaw_deg"] == 12.5 and first["scale"] == 0.1 and first["blur_score"] == 42.0
    assert first["sha256"] == hashlib.sha256(Path(first["path"]).read_bytes()).hexdigest()
    assert crowded["face_count"] == 2 and crowded["yaw_deg"] == 12.5  # largest face is the subject
    assert empty == {**empty, "face_count": 0, "bbox": None, "yaw_deg": None, "scale": None}
    json.dumps(doc)


def test_out_dir_is_write_once(tmp_path: Path) -> None:
    (tmp_path / "frames").mkdir()
    (tmp_path / "frames" / "old.png").write_bytes(b"x")
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"clip")
    with pytest.raises(ValueError, match="write-once"):
        scan_video(video, tmp_path / "frames", detector=_Detector(), detector_config_sha256="d", reader=_reader)


def test_sampling_keeps_the_last_frame_and_bounds_the_count() -> None:
    assert sample_indices(192, 24.0, 2.0) == [*range(0, 192, 12), 191]
    assert sample_indices(5, 24.0, 2.0) == [0, 4]
    with pytest.raises(ValueError, match="frames >"):
        sample_indices(24 * 600, 24.0, 2.0)
