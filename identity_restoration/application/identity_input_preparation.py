from __future__ import annotations

"""Production identity-restoration input for one arbitrary frame (faceless-video LAV-10).

Generalises ``freeze_b01_geometry`` to any keyframe and changes nothing in its pipeline:
``YuNetGeometryExtractor -> crop_for_identity -> hierarchical_face_masks(shape)``. The
crop-local restoration mask is the full-canvas preservation mask cropped by the crop box, so
the two coordinate spaces are one mask by construction.

It also reports the local observations this pipeline actually measures (pinned YuNet
observability + crop-transform round trip). Measurements the repository has no approved
implementation for (blur, occlusion, framing) are listed as UNMEASURED, never guessed.
"""

import hashlib
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Protocol

from PIL import Image

from image_studio_runtime.action_composite.geometry import create_geometry_extractor
from image_studio_runtime.action_composite.masks import crop_for_identity, hierarchical_face_masks
from image_studio_runtime.action_composite.models import FaceGeometry

from ..domain.entities import CropTransform
from .benchmark_geometry import (
    EXPECTED_YUNET_MODEL,
    EXPECTED_YUNET_MODEL_SHA256,
    BenchmarkGeometryAuthorityError,
    _write_png_once,
)

CONTRACT_VERSION = "identity-input-preparation-v1"
MASK_VERSION = "hierarchical_face_v1"
MASK_REGION = "shape"
CROP_SCALE = 2.5
UNMEASURED = ("blur_ok", "occlusion_ok", "framing_ok")


class Observer(Protocol):
    def observe(self, image_bytes: bytes, editable_mask: bytes) -> Any: ...


def policy_version(method_version: str) -> str:
    """Everything that changes the mask bytes for the same input frame."""
    return f"{method_version}|{MASK_VERSION}.{MASK_REGION}|crop{CROP_SCALE}"


def prepare_identity_input(
    image_path: str | Path,
    output_root: str | Path,
    *,
    geometry_extractor: Callable[[Path], FaceGeometry] | None = None,
    observer: Observer | None = None,
) -> dict[str, Any]:
    source = Path(image_path)
    image_bytes = source.read_bytes()
    with Image.open(BytesIO(image_bytes)) as image:
        base = image.convert("RGBA")

    extractor = geometry_extractor or create_geometry_extractor("yunet")
    geometry = extractor(source)
    provenance = getattr(extractor, "last_provenance", None)
    if (
        not isinstance(provenance, dict)
        or provenance.get("backend") != "yunet"
        or provenance.get("model") != EXPECTED_YUNET_MODEL
        or provenance.get("model_sha256") != EXPECTED_YUNET_MODEL_SHA256
    ):
        raise BenchmarkGeometryAuthorityError("YuNet geometry model authority is invalid")

    crop, crop_box = crop_for_identity(base, geometry.face_bbox, scale=CROP_SCALE)
    masks = hierarchical_face_masks(base.size, geometry.face_bbox, version=MASK_VERSION)
    full_canvas_mask = getattr(masks, MASK_REGION).convert("L")
    box = (crop_box.left, crop_box.top, crop_box.right, crop_box.bottom)
    crop_local_mask = full_canvas_mask.crop(box)
    if crop.size != crop_local_mask.size or full_canvas_mask.size != base.size:
        raise BenchmarkGeometryAuthorityError("prepared mask dimensions do not match the frame")
    transform = CropTransform.from_box(*box, target_size=crop.width)

    root = Path(output_root)
    paths = {
        "crop": root / "crop.png",
        "cropLocalMask": root / "crop_local_mask.png",
        "fullCanvasMask": root / "full_canvas_mask.png",
    }
    _write_png_once(paths["crop"], crop)
    _write_png_once(paths["cropLocalMask"], crop_local_mask)
    _write_png_once(paths["fullCanvasMask"], full_canvas_mask)

    measured: dict[str, Any] = {"crop_round_trip_ok": transform.round_trips()}
    observability = None
    if observer is not None:
        report = observer.observe(image_bytes, paths["fullCanvasMask"].read_bytes())
        observability = report.as_dict()
        valid_face = observability["status"] == "VALID"
        measured.update({
            "face_count": observability["faceCount"],
            "bbox_valid": valid_face and observability["bbox"] is not None,
            "landmarks_valid": valid_face and len(observability["landmarks"]) == 5,
            "border_clipped": observability["borderClipped"],
            "face_center_inside_editable_mask": observability["faceCenterInsideEditableMask"],
        })

    method_version = str(provenance.get("method_version", ""))
    return {
        "contractVersion": CONTRACT_VERSION,
        "policyVersion": policy_version(method_version),
        "image": {"sha256": _sha(image_bytes), "width": base.width, "height": base.height},
        "geometryBackend": "yunet",
        "geometryModel": EXPECTED_YUNET_MODEL,
        "geometryModelSha256": EXPECTED_YUNET_MODEL_SHA256,
        "geometryMethodVersion": method_version,
        "geometry": geometry.model_dump(),
        "cropBox": {"left": box[0], "top": box[1], "right": box[2], "bottom": box[3],
                    "targetSize": crop.width},
        "crop": _ref(paths["crop"], crop.size, "crop-local"),
        "cropLocalMask": _ref(paths["cropLocalMask"], crop_local_mask.size, "crop-local"),
        "fullCanvasMask": _ref(paths["fullCanvasMask"], full_canvas_mask.size, "full-canvas"),
        "maskVersion": MASK_VERSION,
        "fullCanvasMaskVersion": f"{MASK_VERSION}_full_canvas",
        "lineage": "YuNetGeometryExtractor -> crop_for_identity -> hierarchical_face_masks.shape",
        "observability": observability,
        "measured": measured,
        "unmeasured": list(UNMEASURED),
    }


def _ref(path: Path, size: tuple[int, int], space: str) -> dict[str, Any]:
    return {"path": str(path), "sha256": _sha(path.read_bytes()), "width": size[0],
            "height": size[1], "coordinateSpace": space}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
