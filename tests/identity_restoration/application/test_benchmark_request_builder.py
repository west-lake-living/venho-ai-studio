from __future__ import annotations

import hashlib
from dataclasses import replace
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from identity_restoration.application.benchmark_contract import load_benchmark_manifest
from identity_restoration.application.benchmark_request_builder import (
    build_benchmark_restore_command,
    validate_benchmark_restore_command,
)
from image_studio_runtime.action_composite.models import BoundingBox, FaceGeometry


ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "contracts" / "identity_restoration" / "benchmark_set.yaml"
A2 = Path(
    "/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/"
    "assets/face-plates/A2_Front_plate.png"
)


def _case() -> dict:
    manifest = load_benchmark_manifest(MANIFEST)
    return next(case for case in manifest["cases"] if case["id"] == "B01")


def _geometry(_: Path) -> FaceGeometry:
    return FaceGeometry(
        face_bbox=BoundingBox(left=300, top=300, right=700, bottom=700),
        head_bbox=BoundingBox(left=120, top=0, right=880, bottom=1000),
        face_scale=400 / 1024,
    )


def test_canonical_b01_command_uses_production_crop_and_masks() -> None:
    command = build_benchmark_restore_command(
        _case(), canonical_a2_path=A2, branch="comfyui-remote",
        run_id="smoke", attempt_id="attempt-1", seed=42,
        geometry_extractor=_geometry,
    )

    assert hashlib.sha256(command.base_canvas_png).hexdigest() == _case()["baseFrame"]["sha256"]
    base_size = Image.open(Path(_case()["baseFrame"]["path"])).size
    crop_size = Image.open(BytesIO(command.crop_png)).size
    crop_mask_size = Image.open(BytesIO(command.mask.editable)).size
    full_mask_size = Image.open(BytesIO(command.full_canvas_mask.editable)).size
    assert base_size == (1024, 1024)
    assert crop_size == (1000, 1000)
    assert crop_mask_size == crop_size
    assert full_mask_size == base_size
    assert command.crop_transform.to_box() == (0, 0, 1000, 1000)
    assert command.crop_transform.target_size == crop_size[0]
    assert command.a2_sha256 == "1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d"
    assert command.seed == 42
    assert command.workflow_id == "face_restore_win_sd15_ipadapter_v2"
    assert command.params.denoise == 0.35
    assert command.params.steps == 20
    assert command.params.cfg == 6
    assert command.params.sampler == "euler"
    assert command.params.scheduler == "normal"


def test_request_override_must_match_canonical_authority() -> None:
    command = build_benchmark_restore_command(
        _case(), canonical_a2_path=A2, branch="comfyui-remote",
        run_id="smoke", attempt_id="attempt-1", seed=42,
        geometry_extractor=_geometry,
    )
    validate_benchmark_restore_command(command, case=_case(), canonical_a2_path=A2)

    with pytest.raises(ValueError, match="A2 authority"):
        validate_benchmark_restore_command(
            replace(command, a2_sha256="0" * 64), case=_case(), canonical_a2_path=A2
        )


def test_builder_rejects_non_frozen_or_wrong_seed() -> None:
    with pytest.raises(ValueError, match="frozen case B01"):
        build_benchmark_restore_command(
            {**_case(), "status": "MISSING"}, canonical_a2_path=A2,
            branch="comfyui-remote", run_id="smoke", attempt_id="attempt-1", seed=42,
            geometry_extractor=_geometry,
        )
    with pytest.raises(ValueError, match="seed"):
        build_benchmark_restore_command(
            _case(), canonical_a2_path=A2, branch="comfyui-remote",
            run_id="smoke", attempt_id="attempt-1", seed=7,
            geometry_extractor=_geometry,
        )
