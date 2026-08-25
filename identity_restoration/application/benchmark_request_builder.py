from __future__ import annotations

"""Build benchmark restore requests from the production geometry path.

This module is deliberately an adapter at the benchmark boundary.  It does
not contain crop or mask geometry; those operations remain in
``image_studio_runtime.action_composite`` and are the same operations used by
the production ActionCompositePipeline.
"""

import hashlib
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Mapping

from PIL import Image

from image_studio_runtime.action_composite.geometry import create_geometry_extractor
from image_studio_runtime.action_composite.masks import crop_for_identity, hierarchical_face_masks
from image_studio_runtime.action_composite.models import FaceGeometry

from .benchmark_contract import (
    EXPECTED_A2_SHA256,
    EXPECTED_REMOTE_PARAMS,
    EXPECTED_WORKFLOW_ID,
    EXPECTED_WORKFLOW_SHA256,
    FROZEN_STATUS,
)
from .dto.restore_command import RestoreCommand
from ..domain.entities import CropTransform, MaskSet
from ..domain.value_objects import RestorationParams


class BenchmarkRequestBuildError(ValueError):
    """Raised when a canonical benchmark request cannot be built safely."""


def build_benchmark_restore_command(
    case: Mapping[str, Any],
    *,
    canonical_a2_path: str | Path,
    branch: str,
    run_id: str,
    attempt_id: str,
    seed: int,
    workflow_id: str = EXPECTED_WORKFLOW_ID,
    workflow_sha256: str = EXPECTED_WORKFLOW_SHA256,
    geometry_extractor: Callable[[Path], FaceGeometry] | None = None,
    geometry_backend: str = "insightface",
) -> RestoreCommand:
    """Build the canonical B01 request without an external request JSON.

    The base frame is authoritative input.  Observed geometry is obtained from
    the existing InsightFace production extractor, then the existing
    ``crop_for_identity`` and ``hierarchical_face_masks`` functions derive all
    request geometry and masks.  A caller may inject a detector only for
    deterministic offline tests; production defaults to InsightFace.
    """

    if branch != "comfyui-remote":
        raise BenchmarkRequestBuildError(
            "canonical bootstrap request builder currently supports comfyui-remote only"
        )
    if case.get("id") != "B01" or case.get("status") != FROZEN_STATUS:
        raise BenchmarkRequestBuildError("canonical bootstrap request requires frozen case B01")
    if seed != 42:
        raise BenchmarkRequestBuildError("benchmark seed must be exactly 42")
    if workflow_id != EXPECTED_WORKFLOW_ID or workflow_sha256 != EXPECTED_WORKFLOW_SHA256:
        raise BenchmarkRequestBuildError("workflow authority does not match the frozen remote pin")

    base_path, base_sha, expected_size = _authoritative_frame(case)
    base_bytes = base_path.read_bytes()
    actual_base_sha = hashlib.sha256(base_bytes).hexdigest()
    if actual_base_sha != base_sha:
        raise BenchmarkRequestBuildError(
            f"B01 base SHA-256 mismatch: expected {base_sha}, got {actual_base_sha}"
        )
    try:
        with Image.open(BytesIO(base_bytes)) as decoded:
            base = decoded.convert("RGBA")
    except Exception as exc:
        raise BenchmarkRequestBuildError(f"B01 base image cannot be decoded: {base_path}") from exc
    if base.size != expected_size:
        raise BenchmarkRequestBuildError(
            f"B01 base dimensions mismatch: expected {expected_size}, got {base.size}"
        )

    a2_path = Path(canonical_a2_path)
    if not a2_path.is_file():
        raise BenchmarkRequestBuildError(f"canonical A2 authority is missing: {a2_path}")
    actual_a2_sha = hashlib.sha256(a2_path.read_bytes()).hexdigest()
    if actual_a2_sha != EXPECTED_A2_SHA256:
        raise BenchmarkRequestBuildError(
            f"canonical A2 SHA-256 mismatch: expected {EXPECTED_A2_SHA256}, got {actual_a2_sha}"
        )

    extractor = geometry_extractor or create_geometry_extractor(geometry_backend)
    try:
        geometry = extractor(base_path)
    except Exception as exc:
        raise BenchmarkRequestBuildError(
            f"B01 production geometry extraction is blocked: {exc}"
        ) from exc
    if not isinstance(geometry, FaceGeometry):
        raise BenchmarkRequestBuildError("production geometry extractor returned an invalid FaceGeometry")
    if geometry.face_bbox.right > base.width or geometry.face_bbox.bottom > base.height:
        raise BenchmarkRequestBuildError("production face geometry lies outside the B01 base image")

    # These are the existing production operations.  Do not replace them with
    # benchmark-specific crop arithmetic or hand-authored mask coordinates.
    crop, crop_box = crop_for_identity(base, geometry.face_bbox)
    masks = hierarchical_face_masks(base.size, geometry.face_bbox, version="hierarchical_face_v1")
    crop_mask = masks.shape.crop((crop_box.left, crop_box.top, crop_box.right, crop_box.bottom))
    full_canvas_mask = masks.shape

    crop_bytes = _png_bytes(crop)
    crop_mask_bytes = _png_bytes(crop_mask.convert("L"))
    full_mask_bytes = _png_bytes(full_canvas_mask.convert("L"))
    if crop.size != crop_mask.size:
        raise BenchmarkRequestBuildError("production crop-local mask dimensions do not match crop")
    if base.size != full_canvas_mask.size:
        raise BenchmarkRequestBuildError("production full-canvas mask dimensions do not match B01")

    command = RestoreCommand(
        run_id=run_id,
        attempt_id=attempt_id,
        restorer_id=branch,
        crop_png=crop_bytes,
        mask=MaskSet(
            editable=crop_mask_bytes,
            feather=crop_mask_bytes,
            version=masks.version,
        ),
        full_canvas_mask=MaskSet(
            editable=full_mask_bytes,
            feather=full_mask_bytes,
            version=f"{masks.version}_full_canvas",
        ),
        base_canvas_png=base_bytes,
        crop_transform=CropTransform.from_box(
            crop_box.left, crop_box.top, crop_box.right, crop_box.bottom, target_size=crop.width
        ),
        a2_path=str(a2_path),
        a2_sha256=actual_a2_sha,
        workflow_id=workflow_id,
        seed=seed,
        params=RestorationParams(
            denoise=float(EXPECTED_REMOTE_PARAMS["denoise"]),
            steps=int(EXPECTED_REMOTE_PARAMS["steps"]),
            cfg=float(EXPECTED_REMOTE_PARAMS["cfg"]),
            sampler=str(EXPECTED_REMOTE_PARAMS["sampler"]),
            scheduler=str(EXPECTED_REMOTE_PARAMS["scheduler"]),
        ),
        geometry_backend=getattr(extractor, "backend_id", geometry_backend),
        geometry_model=getattr(extractor, "model_name", None),
        geometry_model_sha256=getattr(extractor, "expected_model_sha256", None),
    )
    validate_benchmark_restore_command(command, case=case, canonical_a2_path=a2_path)
    return command


def validate_benchmark_restore_command(
    command: RestoreCommand,
    *,
    case: Mapping[str, Any],
    canonical_a2_path: str | Path,
) -> None:
    """Validate a controlled request override against canonical authority.

    This is intentionally stricter than the generic JSON bridge: an override
    cannot change B01 bytes, A2 authority, workflow, seed, params, or the
    production crop/mask dimensional contract.
    """

    if case.get("id") != "B01" or case.get("status") != FROZEN_STATUS:
        raise BenchmarkRequestBuildError("request validation requires frozen case B01")
    base_path, base_sha, expected_size = _authoritative_frame(case)
    if hashlib.sha256(command.base_canvas_png).hexdigest() != base_sha:
        raise BenchmarkRequestBuildError("request base canvas is not the frozen B01 artifact")
    try:
        base_size = Image.open(BytesIO(command.base_canvas_png)).size
        crop_size = Image.open(BytesIO(command.crop_png)).size
        crop_mask_size = Image.open(BytesIO(command.mask.editable)).size
        full_mask_size = Image.open(BytesIO(command.full_canvas_mask.editable)).size
    except Exception as exc:
        raise BenchmarkRequestBuildError("request contains an undecodable image or mask") from exc
    if base_size != expected_size or full_mask_size != expected_size:
        raise BenchmarkRequestBuildError("request full-canvas geometry does not match frozen B01")
    left, top, right, bottom = command.crop_transform.to_box()
    if (right - left, bottom - top) != crop_size or crop_mask_size != crop_size:
        raise BenchmarkRequestBuildError("request crop, crop transform, and crop mask dimensions disagree")
    if left < 0 or top < 0 or right > base_size[0] or bottom > base_size[1]:
        raise BenchmarkRequestBuildError("request crop transform lies outside frozen B01")
    a2_path = Path(canonical_a2_path)
    if command.a2_path != str(a2_path) or command.a2_sha256 != EXPECTED_A2_SHA256:
        raise BenchmarkRequestBuildError("request A2 authority does not match the canonical A2")
    if command.workflow_id != EXPECTED_WORKFLOW_ID or command.seed != 42:
        raise BenchmarkRequestBuildError("request workflow or seed does not match frozen authority")
    actual_params = {
        "denoise": command.params.denoise,
        "steps": command.params.steps,
        "cfg": int(command.params.cfg) if float(command.params.cfg).is_integer() else command.params.cfg,
        "sampler": command.params.sampler,
        "scheduler": command.params.scheduler,
    }
    if actual_params != EXPECTED_REMOTE_PARAMS:
        raise BenchmarkRequestBuildError("request restoration params do not match frozen authority")


def _authoritative_frame(case: Mapping[str, Any]) -> tuple[Path, str, tuple[int, int]]:
    frame = case.get("baseFrame")
    if not isinstance(frame, Mapping):
        raise BenchmarkRequestBuildError("frozen B01 baseFrame is missing")
    path_text = frame.get("path")
    sha256 = frame.get("sha256")
    width, height = frame.get("width"), frame.get("height")
    if not isinstance(path_text, str) or not isinstance(sha256, str):
        raise BenchmarkRequestBuildError("frozen B01 baseFrame authority is incomplete")
    if not isinstance(width, int) or not isinstance(height, int):
        raise BenchmarkRequestBuildError("frozen B01 dimensions are missing")
    path = Path(path_text)
    if not path.is_file():
        raise BenchmarkRequestBuildError(f"frozen B01 base image is missing: {path}")
    return path, sha256, (width, height)


def _png_bytes(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
