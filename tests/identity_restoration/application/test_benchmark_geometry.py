from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from identity_restoration.application.benchmark_contract import load_benchmark_manifest
from identity_restoration.application.benchmark_geometry import (
    EXPECTED_YUNET_MODEL_SHA256,
    BenchmarkGeometryAuthorityError,
    build_frozen_b01_nano_request,
    freeze_b01_geometry,
    load_b01_geometry_authority,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = REPO_ROOT / "contracts/identity_restoration/benchmark_set.yaml"
A2_PATH = REPO_ROOT / "staging/gw-p3/mac-final-20260824-dual-mask/evidence/input_a2.png"
AUTHORITY_PATH = REPO_ROOT / "artifacts/identity-restoration/benchmark-geometry/v2.1/B01/geometry_manifest.json"


def _b01() -> dict:
    manifest = load_benchmark_manifest(MANIFEST_PATH)
    return next(case for case in manifest["cases"] if case["id"] == "B01")


def test_frozen_b01_geometry_has_real_production_lineage():
    authority = load_b01_geometry_authority(AUTHORITY_PATH)

    assert authority["sourceB01Sha256"] == _b01()["baseFrame"]["sha256"]
    assert authority["geometryBackend"] == "yunet"
    assert authority["geometryModelSha256"] == EXPECTED_YUNET_MODEL_SHA256
    assert authority["geometryProvenance"]["detection_count"] == 1
    assert authority["cropTransform"] == {
        "left": 119,
        "top": 0,
        "right": 949,
        "bottom": 1003,
        "targetSize": 830,
    }
    assert authority["cropSize"] == {"width": 830, "height": 1003}
    assert authority["fullCanvasSize"] == {"width": 1024, "height": 1024}

    with Image.open(REPO_ROOT / authority["cropLocalMask"]["path"]) as mask:
        assert mask.size == (830, 1003)
    with Image.open(REPO_ROOT / authority["fullCanvasMask"]["path"]) as mask:
        assert mask.size == (1024, 1024)


def test_freeze_recomputes_masks_through_existing_geometry_path(tmp_path: Path):
    authority = freeze_b01_geometry(_b01(), canonical_a2_path=A2_PATH, output_root=tmp_path)

    assert authority["lineage"] == "YuNetGeometryExtractor -> crop_for_identity -> hierarchical_face_masks"
    assert Path(authority["cropLocalMask"]["path"]).is_file()
    assert Path(authority["fullCanvasMask"]["path"]).is_file()
    assert Path(authority["manifestPath"]).is_file()


def test_builder_returns_full_canvas_mask_and_preserves_lineage():
    request = build_frozen_b01_nano_request(
        _b01(),
        geometry_authority_path=AUTHORITY_PATH,
        canonical_a2_path=A2_PATH,
        run_id="smoke-run",
        attempt_id="attempt-001",
        seed=42,
    )

    assert request.operation == "masked_edit"
    assert request.mask_path == (
        REPO_ROOT / "artifacts/identity-restoration/benchmark-geometry/v2.1/B01/full_canvas_mask.png"
    ).resolve()
    assert request.crop_transform == {"left": 119, "top": 0, "right": 949, "bottom": 1003, "targetSize": 830}
    assert request.lineage["cropLocalMaskSha256"]
    assert request.lineage["fullCanvasMaskSha256"]
    assert request.seed_supported is False


def test_builder_fails_closed_on_wrong_seed_or_missing_geometry():
    with pytest.raises(BenchmarkGeometryAuthorityError, match="seed"):
        build_frozen_b01_nano_request(
            _b01(),
            geometry_authority_path=AUTHORITY_PATH,
            canonical_a2_path=A2_PATH,
            run_id="smoke-run",
            attempt_id="attempt-001",
            seed=7,
        )

    with pytest.raises(BenchmarkGeometryAuthorityError):
        build_frozen_b01_nano_request(
            _b01(),
            geometry_authority_path=AUTHORITY_PATH.with_name("missing.json"),
            canonical_a2_path=A2_PATH,
            run_id="smoke-run",
            attempt_id="attempt-001",
            seed=42,
        )
