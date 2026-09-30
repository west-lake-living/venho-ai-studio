"""Production identity input preparation reuses the frozen B01 pipeline byte-for-byte."""

from __future__ import annotations

import hashlib
import json
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from identity_restoration.application.benchmark_geometry import BenchmarkGeometryAuthorityError
from identity_restoration.application.identity_input_preparation import (
    UNMEASURED,
    prepare_identity_input,
)
from identity_restoration.interface.json_bridge import parse_restore_command
from image_studio_runtime.action_composite.models import BoundingBox, FaceGeometry

REPO = Path(__file__).resolve().parents[3]
B01_MANIFEST = REPO / "artifacts/identity-restoration/benchmark-geometry/v2.1/B01/geometry_manifest.json"


class _Extractor:
    def __init__(self, bbox: BoundingBox, provenance: dict) -> None:
        self.bbox = bbox
        self.last_provenance = provenance

    def __call__(self, path: Path) -> FaceGeometry:
        return FaceGeometry(face_bbox=self.bbox, head_bbox=self.bbox, face_scale=1.0)


def _provenance(**overrides: object) -> dict:
    value = {"backend": "yunet", "model": "face_detection_yunet_2023mar.onnx",
             "model_sha256": "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
             "method_version": "opencv-zoo-yunet-2023mar-pnp-v1"}
    value.update(overrides)
    return value


def _frame(tmp_path: Path) -> Path:
    path = tmp_path / "frame.png"
    Image.new("RGB", (200, 160), (120, 100, 90)).save(path)
    return path


def test_masks_are_one_mask_in_two_spaces_and_unmeasured_checks_are_not_guessed(tmp_path: Path) -> None:
    out = prepare_identity_input(
        _frame(tmp_path), tmp_path / "out",
        geometry_extractor=_Extractor(BoundingBox(left=70, top=40, right=130, bottom=110), _provenance()),
    )
    box = out["cropBox"]
    full = Image.open(out["fullCanvasMask"]["path"])
    local = Image.open(out["cropLocalMask"]["path"])
    assert full.size == (200, 160)
    assert full.crop((box["left"], box["top"], box["right"], box["bottom"])).tobytes() == local.tobytes()
    assert out["measured"] == {"crop_round_trip_ok": True}  # no observer ⇒ nothing else claimed
    assert out["unmeasured"] == list(UNMEASURED)
    assert out["policyVersion"] == "opencv-zoo-yunet-2023mar-pnp-v1|hierarchical_face_v1.shape|crop2.5"


def test_wrong_detector_model_is_refused(tmp_path: Path) -> None:
    with pytest.raises(BenchmarkGeometryAuthorityError):
        prepare_identity_input(
            _frame(tmp_path), tmp_path / "out",
            geometry_extractor=_Extractor(BoundingBox(left=70, top=40, right=130, bottom=110),
                                          _provenance(model_sha256="0" * 64)),
        )


def _png(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _request(tmp_path: Path, prepared: dict, frame: Path, crop_mask: Path | None = None) -> dict:
    local = crop_mask or Path(prepared["cropLocalMask"]["path"])
    return {
        "runId": "run-prep", "attemptId": "attempt-1", "restorerId": "mock",
        "basePath": str(frame), "cropPath": prepared["crop"]["path"],
        "maskEditablePath": str(local),
        "maskEditableSha256": hashlib.sha256(local.read_bytes()).hexdigest(),
        "fullCanvasMaskPath": prepared["fullCanvasMask"]["path"],
        "fullCanvasMaskSha256": prepared["fullCanvasMask"]["sha256"],
        "cropBox": prepared["cropBox"], "a2Path": "a2.png", "a2Sha256": "a" * 64,
        "workflowId": "mock", "seed": 1,
        "params": {"denoise": 0.35, "steps": 20, "cfg": 6.0, "sampler": "euler", "scheduler": "normal"},
    }


def test_restore_request_refuses_a_crop_mask_that_is_not_the_full_canvas_crop(tmp_path: Path) -> None:
    frame = _frame(tmp_path)
    prepared = prepare_identity_input(
        frame, tmp_path / "out",
        geometry_extractor=_Extractor(BoundingBox(left=70, top=40, right=130, bottom=110), _provenance()),
    )
    parse_restore_command(_request(tmp_path, prepared, frame))  # consistent pair parses
    other = tmp_path / "other_mask.png"
    size = Image.open(prepared["cropLocalMask"]["path"]).size
    other.write_bytes(_png(Image.new("L", size, 255)))
    with pytest.raises(ValueError, match="not the full-canvas mask cropped"):
        parse_restore_command(_request(tmp_path, prepared, frame, crop_mask=other))
    tampered = _request(tmp_path, prepared, frame)
    tampered["maskEditableSha256"] = "0" * 64
    with pytest.raises(ValueError, match="crop-local mask SHA-256 mismatch"):
        parse_restore_command(tampered)


@pytest.mark.skipif(not B01_MANIFEST.is_file(), reason="frozen B01 geometry authority not present")
def test_real_yunet_reproduces_the_frozen_b01_masks_and_observes_one_face(tmp_path: Path) -> None:
    pytest.importorskip("cv2")
    authority = json.loads(B01_MANIFEST.read_text())
    frame = Path(authority["sourceB01Path"])
    if not frame.is_file():
        pytest.skip("B01 source frame not present on this machine")
    from identity_restoration.infrastructure.face_observability_yunet import (
        create_pinned_yunet_observability_service,
    )

    out = prepare_identity_input(frame, tmp_path / "b01", observer=create_pinned_yunet_observability_service())
    assert out["cropLocalMask"]["sha256"] == authority["cropLocalMask"]["sha256"]
    assert out["fullCanvasMask"]["sha256"] == authority["fullCanvasMask"]["sha256"]
    assert {k: out["cropBox"][k] for k in ("left", "top", "right", "bottom")} == {
        k: authority["cropTransform"][k] for k in ("left", "top", "right", "bottom")
    }
    measured = out["measured"]
    assert measured["face_count"] == 1 and measured["bbox_valid"] and measured["landmarks_valid"]
    assert measured["crop_round_trip_ok"] is True
    assert out["observability"]["status"] == "VALID"
