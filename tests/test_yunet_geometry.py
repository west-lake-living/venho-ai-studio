from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image

from identity_restoration.application.benchmark_contract import load_benchmark_manifest
from identity_restoration.application.benchmark_request_builder import build_benchmark_restore_command
from image_studio_runtime.action_composite.geometry import (
    FaceGeometryEvidenceBlocked,
    YuNetGeometryExtractor,
    create_geometry_extractor,
)


ROOT = Path(__file__).resolve().parents[1]
B01 = Path(
    "/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/"
    "photos-ai/2026/12-08-linh-an-a2-front-closeup-1k/run-202608121022/variant-001/image.png"
)
A2 = Path(
    "/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/"
    "assets/face-plates/A2_Front_plate.png"
)
MODEL_SHA = "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"


class _Detector:
    def __init__(self, rows: np.ndarray) -> None:
        self.rows = rows
        self.input_size = None

    def setInputSize(self, size):  # noqa: N802 - OpenCV API spelling
        self.input_size = size

    def detect(self, image):
        assert image.shape[2] == 3
        return len(self.rows), self.rows


def _row() -> np.ndarray:
    return np.asarray([368, 186, 332, 467,
                       449, 359, 608, 353, 529, 460, 465, 529, 602, 524,
                       0.91], dtype=np.float32)


def test_yunet_real_b01_geometry_and_provenance() -> None:
    extractor = YuNetGeometryExtractor()
    geometry = extractor.extract(B01)
    assert hashlib.sha256(B01.read_bytes()).hexdigest() == (
        "e7b00d4a65b2cc97e274e3c00f96e091bda0e614778df5a2d43f17cc3793faf9"
    )
    assert geometry.face_bbox.left >= 0
    assert geometry.face_bbox.right <= 1024
    assert extractor.last_provenance is not None
    assert extractor.last_provenance["backend"] == "yunet"
    assert extractor.last_provenance["model_sha256"] == MODEL_SHA
    assert extractor.last_provenance["detection_count"] == 1
    assert len(extractor.last_provenance["landmarks"]) == 5


def test_yunet_uses_existing_crop_and_mask_contract() -> None:
    manifest = load_benchmark_manifest(ROOT / "contracts/identity_restoration/benchmark_set.yaml")
    case = next(item for item in manifest["cases"] if item["id"] == "B01")
    extractor = YuNetGeometryExtractor()
    command = build_benchmark_restore_command(
        case, canonical_a2_path=A2, branch="comfyui-remote",
        run_id="yunet-test", attempt_id="1", seed=42,
        geometry_extractor=extractor, geometry_backend="yunet",
    )
    crop_size = Image.open(BytesIO(command.crop_png)).size
    crop_mask_size = Image.open(BytesIO(command.mask.editable)).size
    full_mask_size = Image.open(BytesIO(command.full_canvas_mask.editable)).size
    assert crop_mask_size == crop_size
    assert full_mask_size == (1024, 1024)
    assert command.crop_transform.round_trips()
    assert command.geometry_backend == "yunet"
    assert command.geometry_model == "face_detection_yunet_2023mar.onnx"
    assert command.geometry_model_sha256 == MODEL_SHA


def test_yunet_requires_exactly_one_face_and_valid_bbox() -> None:
    image = B01
    one = _Detector(np.asarray([_row()]))
    geometry = YuNetGeometryExtractor(detector=one, cv2_module=cv2).extract(image)
    assert geometry.face_bbox.width == 332

    for rows, message in (
        (np.empty((0, 15), dtype=np.float32), "detected 0"),
        (np.vstack([_row(), _row()]), "detected 2"),
    ):
        with pytest.raises(FaceGeometryEvidenceBlocked, match=message):
            YuNetGeometryExtractor(
                detector=_Detector(rows), cv2_module=cv2
            ).extract(image)

    invalid = _row().copy()
    invalid[0] = -1
    with pytest.raises(FaceGeometryEvidenceBlocked, match="outside decoded image bounds"):
        YuNetGeometryExtractor(
            detector=_Detector(np.asarray([invalid])), cv2_module=cv2
        ).extract(image)


def test_yunet_model_hash_and_backend_selection_fail_closed() -> None:
    with pytest.raises(FaceGeometryEvidenceBlocked, match="SHA-256 mismatch"):
        YuNetGeometryExtractor(
            detector=_Detector(np.asarray([_row()])), cv2_module=cv2,
            expected_model_sha256="0" * 64,
        ).extract(B01)
    with pytest.raises(FaceGeometryEvidenceBlocked, match="Unsupported geometry backend"):
        create_geometry_extractor("missing-backend")
