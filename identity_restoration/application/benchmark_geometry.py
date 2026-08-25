from __future__ import annotations

"""Canonical, production-derived benchmark geometry authority."""

import hashlib
import json
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Mapping

from PIL import Image

from image_studio_runtime.action_composite.geometry import create_geometry_extractor
from image_studio_runtime.action_composite.masks import crop_for_identity, hierarchical_face_masks
from image_studio_runtime.action_composite.models import FaceGeometry

from .benchmark_contract import EXPECTED_A2_SHA256, FROZEN_STATUS
from .benchmark_executor import NanoBananaEditRequest


EXPECTED_YUNET_MODEL = "face_detection_yunet_2023mar.onnx"
EXPECTED_YUNET_MODEL_SHA256 = "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"
GEOMETRY_VERSION = "benchmark-b01-geometry-v2.1"


class BenchmarkGeometryAuthorityError(ValueError):
    pass


def freeze_b01_geometry(
    case: Mapping[str, Any],
    *,
    canonical_a2_path: str | Path,
    output_root: str | Path,
    geometry_extractor: Callable[[Path], FaceGeometry] | None = None,
) -> dict[str, Any]:
    """Generate stable B01 mask artifacts from the existing production path.

    This function calls only the existing YuNet extractor, crop, and
    hierarchical mask functions. It refuses to overwrite an existing authority
    with different bytes.
    """
    if case.get("id") != "B01" or case.get("status") != FROZEN_STATUS:
        raise BenchmarkGeometryAuthorityError("B01 must be frozen before geometry can be frozen")
    base_path, base_sha, base_size = _frame(case)
    actual_base_sha = _sha(base_path)
    if actual_base_sha != base_sha:
        raise BenchmarkGeometryAuthorityError(
            f"B01 SHA mismatch: expected {base_sha}, got {actual_base_sha}"
        )
    with Image.open(base_path) as image:
        if image.size != base_size:
            raise BenchmarkGeometryAuthorityError(f"B01 dimensions mismatch: expected {base_size}, got {image.size}")
        base = image.convert("RGBA")

    a2_path = Path(canonical_a2_path)
    if not a2_path.is_file() or _sha(a2_path) != EXPECTED_A2_SHA256:
        raise BenchmarkGeometryAuthorityError("canonical A2 authority is missing or has the wrong SHA-256")

    extractor = geometry_extractor or create_geometry_extractor("yunet")
    geometry = extractor(base_path)
    provenance = getattr(extractor, "last_provenance", None)
    if not isinstance(provenance, dict):
        raise BenchmarkGeometryAuthorityError("YuNet geometry provenance is missing")
    if (
        provenance.get("backend") != "yunet"
        or provenance.get("model") != EXPECTED_YUNET_MODEL
        or provenance.get("model_sha256") != EXPECTED_YUNET_MODEL_SHA256
    ):
        raise BenchmarkGeometryAuthorityError("YuNet geometry model authority is invalid")

    crop, crop_box = crop_for_identity(base, geometry.face_bbox)
    masks = hierarchical_face_masks(base.size, geometry.face_bbox, version="hierarchical_face_v1")
    crop_local_mask = masks.shape.crop((crop_box.left, crop_box.top, crop_box.right, crop_box.bottom)).convert("L")
    full_canvas_mask = masks.shape.convert("L")
    if crop.size != crop_local_mask.size:
        raise BenchmarkGeometryAuthorityError("crop-local mask dimensions do not match production crop")
    if full_canvas_mask.size != base.size:
        raise BenchmarkGeometryAuthorityError("full-canvas mask dimensions do not match B01")

    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    crop_path = root / "crop_local_mask.png"
    full_path = root / "full_canvas_mask.png"
    _write_png_once(crop_path, crop_local_mask)
    _write_png_once(full_path, full_canvas_mask)

    crop_transform = {
        "left": crop_box.left,
        "top": crop_box.top,
        "right": crop_box.right,
        "bottom": crop_box.bottom,
        "targetSize": crop.width,
    }
    authority = {
        "version": GEOMETRY_VERSION,
        "caseId": "B01",
        "sourceB01Path": str(base_path),
        "sourceB01Sha256": base_sha,
        "sourceB01Dimensions": {"width": base.width, "height": base.height},
        "a2AuthorityPath": str(a2_path),
        "a2AuthoritySha256": EXPECTED_A2_SHA256,
        "geometryBackend": "yunet",
        "geometryModel": EXPECTED_YUNET_MODEL,
        "geometryModelSha256": EXPECTED_YUNET_MODEL_SHA256,
        "geometryMethodVersion": provenance.get("method_version"),
        "geometry": geometry.model_dump(),
        "geometryProvenance": provenance,
        "cropTransform": crop_transform,
        "cropSize": {"width": crop.width, "height": crop.height},
        "fullCanvasSize": {"width": base.width, "height": base.height},
        "maskVersion": masks.version,
        "cropLocalMask": {
            "path": str(crop_path),
            "sha256": _sha(crop_path),
            "width": crop_local_mask.width,
            "height": crop_local_mask.height,
            "coordinateSpace": "crop-local",
        },
        "fullCanvasMask": {
            "path": str(full_path),
            "sha256": _sha(full_path),
            "width": full_canvas_mask.width,
            "height": full_canvas_mask.height,
            "coordinateSpace": "full-canvas",
            "version": f"{masks.version}_full_canvas",
        },
        "createdAtUtc": datetime.now(timezone.utc).isoformat(),
        "lineage": "YuNetGeometryExtractor -> crop_for_identity -> hierarchical_face_masks",
    }
    manifest_path = root / "geometry_manifest.json"
    _write_json_once(manifest_path, authority)
    authority["manifestPath"] = str(manifest_path)
    authority["manifestSha256"] = _sha(manifest_path)
    return authority


def load_b01_geometry_authority(path: str | Path) -> dict[str, Any]:
    authority_path = Path(path)
    try:
        payload = json.loads(authority_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BenchmarkGeometryAuthorityError(f"B01 geometry authority cannot be read: {authority_path}") from exc
    if not isinstance(payload, dict):
        raise BenchmarkGeometryAuthorityError("B01 geometry authority must be a JSON object")
    return payload


def build_frozen_b01_nano_request(
    case: Mapping[str, Any],
    *,
    geometry_authority_path: str | Path,
    canonical_a2_path: str | Path,
    run_id: str,
    attempt_id: str,
    seed: int,
) -> NanoBananaEditRequest:
    """Build Nano's full-canvas input contract from frozen geometry only."""
    if seed != 42:
        raise BenchmarkGeometryAuthorityError("benchmark seed must be exactly 42")
    authority_path = Path(geometry_authority_path)
    authority = load_b01_geometry_authority(geometry_authority_path)
    base_path, base_sha, base_size = _frame(case)
    if authority.get("sourceB01Sha256") != base_sha:
        raise BenchmarkGeometryAuthorityError("geometry authority does not match B01 SHA")
    if authority.get("a2AuthoritySha256") != EXPECTED_A2_SHA256:
        raise BenchmarkGeometryAuthorityError("geometry authority does not match A2 SHA")
    if authority.get("geometryModelSha256") != EXPECTED_YUNET_MODEL_SHA256:
        raise BenchmarkGeometryAuthorityError("geometry authority does not match YuNet model SHA")
    a2_path = Path(canonical_a2_path)
    if _sha(a2_path) != EXPECTED_A2_SHA256:
        raise BenchmarkGeometryAuthorityError("canonical A2 SHA mismatch")
    full = authority.get("fullCanvasMask")
    crop = authority.get("cropLocalMask")
    if not isinstance(full, Mapping) or not isinstance(crop, Mapping):
        raise BenchmarkGeometryAuthorityError("geometry authority lacks both mask artifacts")
    full_path = _resolve_authority_artifact_path(full.get("path"), authority_path)
    crop_path = _resolve_authority_artifact_path(crop.get("path"), authority_path)
    _verify_mask(full_path, full, expected_size=base_size, coordinate_space="full-canvas")
    crop_transform = authority.get("cropTransform")
    crop_size = authority.get("cropSize")
    if not isinstance(crop_transform, Mapping) or not isinstance(crop_size, Mapping):
        raise BenchmarkGeometryAuthorityError("geometry authority crop transform is missing")
    expected_crop_size = (int(crop_size["width"]), int(crop_size["height"]))
    transform_size = (
        int(crop_transform["right"]) - int(crop_transform["left"]),
        int(crop_transform["bottom"]) - int(crop_transform["top"]),
    )
    if transform_size != expected_crop_size:
        raise BenchmarkGeometryAuthorityError("cropTransform does not match the frozen crop dimensions")
    _verify_mask(crop_path, crop, expected_size=expected_crop_size, coordinate_space="crop-local")
    return NanoBananaEditRequest(
        base_path=base_path,
        a2_path=a2_path,
        mask_path=full_path,
        crop_transform=dict(crop_transform),
        mask_version=str(authority.get("maskVersion")),
        seed_supported=False,
        operation="masked_edit",
        lineage={
            "geometryAuthorityPath": str(Path(geometry_authority_path)),
            "geometryAuthorityVersion": authority.get("version"),
            "geometryAuthoritySha256": _sha(Path(geometry_authority_path)),
            "cropLocalMaskPath": str(crop_path),
            "cropLocalMaskSha256": crop.get("sha256"),
            "fullCanvasMaskPath": str(full_path),
            "fullCanvasMaskSha256": full.get("sha256"),
            "runId": run_id,
            "attemptId": attempt_id,
        },
        geometry_authority_path=Path(geometry_authority_path),
    )


def _frame(case: Mapping[str, Any]) -> tuple[Path, str, tuple[int, int]]:
    frame = case.get("baseFrame")
    if not isinstance(frame, Mapping):
        raise BenchmarkGeometryAuthorityError("B01 baseFrame is missing")
    path = Path(str(frame.get("path", "")))
    sha = frame.get("sha256")
    width, height = frame.get("width"), frame.get("height")
    if not path.is_file() or not isinstance(sha, str) or not isinstance(width, int) or not isinstance(height, int):
        raise BenchmarkGeometryAuthorityError("B01 baseFrame authority is incomplete")
    return path, sha, (width, height)


def _verify_mask(path: Path, metadata: Mapping[str, Any], *, expected_size: tuple[int, int], coordinate_space: str) -> None:
    if metadata.get("coordinateSpace") != coordinate_space:
        raise BenchmarkGeometryAuthorityError(f"mask coordinate space must be {coordinate_space}")
    if not path.is_file() or _sha(path) != metadata.get("sha256"):
        raise BenchmarkGeometryAuthorityError(f"{coordinate_space} mask is missing or SHA-256 mismatched")
    with Image.open(path) as image:
        if image.size != expected_size:
            raise BenchmarkGeometryAuthorityError(
                f"{coordinate_space} mask dimensions mismatch: expected {expected_size}, got {image.size}"
            )


def _resolve_authority_artifact_path(value: Any, authority_path: Path) -> Path:
    """Resolve manifest paths without changing the persisted authority text."""
    if not isinstance(value, str) or not value:
        raise BenchmarkGeometryAuthorityError("geometry authority artifact path is missing")
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    search_roots = [Path.cwd(), *authority_path.parents]
    for root in search_roots:
        resolved = root / candidate
        if resolved.is_file():
            return resolved
    return candidate


def _write_png_once(path: Path, image: Image.Image) -> None:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    data = buffer.getvalue()
    if path.exists():
        if path.read_bytes() != data:
            raise BenchmarkGeometryAuthorityError(f"refusing to overwrite different geometry artifact: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _write_json_once(path: Path, payload: Mapping[str, Any]) -> None:
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if path.exists():
        if path.read_bytes() != data:
            raise BenchmarkGeometryAuthorityError(f"refusing to overwrite different geometry manifest: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
