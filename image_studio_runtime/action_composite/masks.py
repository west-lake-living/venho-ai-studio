from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from PIL import Image, ImageDraw, ImageFilter

from .models import BoundingBox


def face_mask(size: tuple[int, int], bbox: BoundingBox, *, feather: int = 8) -> Image.Image:
    """Create a soft elliptical face mask; pixels outside it stay untouched."""
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((bbox.left, bbox.top, bbox.right, bbox.bottom), fill=255)
    return mask.filter(ImageFilter.GaussianBlur(radius=max(0, feather)))


@dataclass(frozen=True)
class HierarchicalFaceMasks:
    """Conservative masks for staged identity repair.

    ``core`` owns identity-bearing features, ``shape`` owns cheek/jaw structure,
    and ``boundary`` is reserved for hairline and neck harmonisation. The masks
    are intentionally disjoint at their hard regions and feathered only at the
    seam, so callers can preserve all non-face pixels byte-for-byte.
    """

    core: Image.Image
    shape: Image.Image
    boundary: Image.Image
    version: str = "hierarchical_face_v1"

    def as_manifest(self) -> dict[str, object]:
        return {"version": self.version, "regions": ["core", "shape", "boundary"]}


def hierarchical_face_masks(size: tuple[int, int], bbox: BoundingBox, *, feather: int = 6,
                            version: str = "hierarchical_face_v1") -> HierarchicalFaceMasks:
    """Build core/shape/boundary repair masks from one locked face bbox."""
    width, height = size
    core_box = BoundingBox(
        left=round(bbox.left + bbox.width * 0.16),
        top=round(bbox.top + bbox.height * 0.16),
        right=round(bbox.right - bbox.width * 0.16),
        bottom=round(bbox.bottom - bbox.height * 0.10),
    )
    shape_box = bbox.padded(0.06, width, height)
    boundary_box = bbox.padded(0.24, width, height)
    core = face_mask(size, core_box, feather=feather)
    shape = face_mask(size, shape_box, feather=feather)
    boundary = face_mask(size, boundary_box, feather=feather + 2)
    return HierarchicalFaceMasks(core=core, shape=shape, boundary=boundary, version=version)


def geometry_preserving_identity_mask(
    size: tuple[int, int],
    face_bbox: BoundingBox,
    landmarks: Iterable[tuple[float, float]],
    *,
    feather: int = 8,
    version: str = "geometry-preserving-identity-v1",
) -> tuple[Image.Image, dict[str, Any]]:
    """Build an analysis/restoration mask for identity-bearing inner features.

    The feature centers come from the detector's five landmarks in InsightFace
    order: left eye, right eye, nose, left mouth, right mouth.  Radii are
    ratios of the observed face box, so this is not tied to one image's pixel
    coordinates.  The outer contour, head boundary, and crop context remain
    hard-preserved.
    """
    if len(size) != 2 or size[0] <= 0 or size[1] <= 0:
        raise ValueError("mask size must be positive")
    points = [(float(x), float(y)) for x, y in landmarks]
    if len(points) != 5:
        raise ValueError("exactly five detector landmarks are required")
    width, height = size
    margin_x = max(1, round(face_bbox.width * 0.10))
    margin_y = max(1, round(face_bbox.height * 0.10))
    inner = (
        max(0, face_bbox.left + margin_x),
        max(0, face_bbox.top + margin_y),
        min(width, face_bbox.right - margin_x),
        min(height, face_bbox.bottom - margin_y),
    )
    if inner[2] <= inner[0] or inner[3] <= inner[1]:
        raise ValueError("face geometry leaves no inner identity region")
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    fw, fh = face_bbox.width, face_bbox.height

    def ellipse(center: tuple[float, float], rx_ratio: float, ry_ratio: float) -> None:
        rx, ry = max(1, round(fw * rx_ratio)), max(1, round(fh * ry_ratio))
        box = (round(center[0] - rx), round(center[1] - ry),
               round(center[0] + rx), round(center[1] + ry))
        draw.ellipse((max(inner[0], box[0]), max(inner[1], box[1]),
                      min(inner[2], box[2]), min(inner[3], box[3])), fill=255)

    left_eye, right_eye, nose, left_mouth, right_mouth = points
    ellipse(left_eye, 0.13, 0.075)
    ellipse(right_eye, 0.13, 0.075)
    ellipse(nose, 0.13, 0.14)
    mouth = ((left_mouth[0] + right_mouth[0]) / 2, (left_mouth[1] + right_mouth[1]) / 2)
    ellipse(mouth, 0.18, 0.095)
    # Central cheeks are derived from the landmark triangle, not fixed pixels.
    ellipse(((left_eye[0] + nose[0]) / 2, (left_eye[1] + nose[1]) / 2), 0.12, 0.11)
    ellipse(((right_eye[0] + nose[0]) / 2, (right_eye[1] + nose[1]) / 2), 0.12, 0.11)
    feathered = mask.filter(ImageFilter.GaussianBlur(radius=max(0, feather)))
    nonzero = sum(1 for value in feathered.getdata() if value > 0)
    metadata = {
        "version": version,
        "source": "InsightFace buffalo_l five-point landmarks",
        "face_bbox": face_bbox.model_dump(),
        "landmark_order": ["left_eye", "right_eye", "nose", "left_mouth", "right_mouth"],
        "landmarks": [[x, y] for x, y in points],
        "inner_region_ratios": {"margin_x": 0.10, "margin_y": 0.10},
        "feature_radius_ratios": {
            "eyes": [0.13, 0.075], "nose": [0.13, 0.14],
            "mouth": [0.18, 0.095], "central_cheeks": [0.12, 0.11],
        },
        "feather_method": "PIL.ImageFilter.GaussianBlur",
        "feather_radius": feather,
        "dilation": 0,
        "erosion": 0,
        "mask_bbox": _mask_bbox(feathered),
        "nonzero_pixel_count": nonzero,
        "coverage_ratio": nonzero / float(width * height),
        "touches_crop_boundary": bool(
            feathered.getbbox() and (
                feathered.getbbox()[0] <= 0 or feathered.getbbox()[1] <= 0 or
                feathered.getbbox()[2] >= width or feathered.getbbox()[3] >= height
            )
        ),
    }
    return feathered, metadata


def _mask_bbox(mask: Image.Image) -> dict[str, int] | None:
    bounds = mask.getbbox()
    if bounds is None:
        return None
    left, top, right, bottom = bounds
    return {"left": left, "top": top, "right": right, "bottom": bottom}


def crop_for_identity(image: Image.Image, bbox: BoundingBox, *, scale: float = 2.5) -> tuple[Image.Image, BoundingBox]:
    # A scale below 1 turns the padding negative and inverts the box; the crop
    # exists to give the restorer more context, never less.
    if scale < 1.0:
        raise ValueError("crop scale must be >= 1.0")
    crop_box = bbox.padded((scale - 1) / 2, image.width, image.height)
    return image.crop((crop_box.left, crop_box.top, crop_box.right, crop_box.bottom)), crop_box
