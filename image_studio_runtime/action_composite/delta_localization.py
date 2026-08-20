"""Deterministic, analysis-only helpers for restoration delta localization."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
from PIL import Image

from .models import BoundingBox


@dataclass(frozen=True)
class RegionDelta:
    mean_absolute_rgb_delta: float
    changed_pixel_percentage: float
    pixel_count: int


def geometry_drift(reference_bbox: tuple[float, float, float, float],
                   observed_bbox: tuple[float, float, float, float],
                   *, reference_angles: tuple[float, float, float] | None = None,
                   observed_angles: tuple[float, float, float] | None = None,
                   reference_face_scale: float | None = None,
                   observed_face_scale: float | None = None) -> dict[str, object]:
    """Measure geometry deltas without applying a pass/fail threshold."""
    rcx = (reference_bbox[0] + reference_bbox[2]) / 2
    rcy = (reference_bbox[1] + reference_bbox[3]) / 2
    ocx = (observed_bbox[0] + observed_bbox[2]) / 2
    ocy = (observed_bbox[1] + observed_bbox[3]) / 2
    rw, rh = reference_bbox[2] - reference_bbox[0], reference_bbox[3] - reference_bbox[1]
    ow, oh = observed_bbox[2] - observed_bbox[0], observed_bbox[3] - observed_bbox[1]
    return {
        "bbox_center_delta_px": [ocx - rcx, ocy - rcy],
        "bbox_width_ratio": ow / rw if rw else None,
        "bbox_height_ratio": oh / rh if rh else None,
        "yaw_delta": observed_angles[0] - reference_angles[0] if reference_angles and observed_angles else None,
        "pitch_delta": observed_angles[1] - reference_angles[1] if reference_angles and observed_angles else None,
        "roll_delta": observed_angles[2] - reference_angles[2] if reference_angles and observed_angles else None,
        "face_scale_delta": observed_face_scale - reference_face_scale
        if observed_face_scale is not None and reference_face_scale is not None else None,
    }


def resize_restored_for_analysis(restored: Image.Image, target_size: tuple[int, int]) -> Image.Image:
    """Return a derived analysis image; callers retain the raw source untouched."""
    return restored.convert("RGB").resize(target_size, Image.Resampling.BICUBIC)


def rgb_delta(original: Image.Image, restored: Image.Image) -> tuple[np.ndarray, np.ndarray]:
    left = np.asarray(original.convert("RGB"), dtype=np.int16)
    right = np.asarray(restored.convert("RGB"), dtype=np.int16)
    if left.shape != right.shape:
        raise ValueError("Delta inputs must have identical dimensions")
    absolute = np.abs(left - right).astype(np.uint8)
    normalized = absolute.max(axis=2)
    return absolute, normalized


def diagnostic_zone_masks(*, crop_size: tuple[int, int], face_bbox_full_frame: tuple[float, float, float, float],
                          crop_box: BoundingBox) -> dict[str, np.ndarray]:
    """Return a non-overlapping full-crop partition based on the detected face box.

    Five InsightFace points cannot delineate forehead, cheeks, and jaw exactly,
    so these are deterministic face-bbox-relative diagnostic zones.  They are
    only used for attribution experiments, not scoring or restoration.
    """
    width, height = crop_size
    face_left = max(0, int(round(face_bbox_full_frame[0] - crop_box.left)))
    face_top = max(0, int(round(face_bbox_full_frame[1] - crop_box.top)))
    face_right = min(width, int(round(face_bbox_full_frame[2] - crop_box.left)))
    face_bottom = min(height, int(round(face_bbox_full_frame[3] - crop_box.top)))
    if face_left >= face_right or face_top >= face_bottom:
        raise ValueError("Detected face bbox is not inside the crop placement")
    masks = {name: np.zeros((height, width), dtype=bool) for name in (
        "forehead_upper_head", "left_eye", "right_eye", "nose", "mouth",
        "left_cheek", "right_cheek", "jaw_chin", "surrounding_context",
    )}
    face = np.zeros((height, width), dtype=bool)
    face[face_top:face_bottom, face_left:face_right] = True
    masks["surrounding_context"] = ~face
    face_width = face_right - face_left
    face_height = face_bottom - face_top
    x35, x50, x65 = (face_left + round(face_width * ratio) for ratio in (0.35, 0.50, 0.65))
    x25, x75 = (face_left + round(face_width * ratio) for ratio in (0.25, 0.75))
    y26, y48, y70, y84 = (face_top + round(face_height * ratio) for ratio in (0.26, 0.48, 0.70, 0.84))
    masks["forehead_upper_head"][face_top:y26, face_left:face_right] = True
    masks["left_eye"][y26:y48, face_left:x50] = True
    masks["right_eye"][y26:y48, x50:face_right] = True
    masks["left_cheek"][y48:y70, face_left:x35] = True
    masks["nose"][y48:y70, x35:x65] = True
    masks["right_cheek"][y48:y70, x65:face_right] = True
    masks["left_cheek"][y70:y84, face_left:x25] = True
    masks["mouth"][y70:y84, x25:x75] = True
    masks["right_cheek"][y70:y84, x75:face_right] = True
    masks["jaw_chin"][y84:face_bottom, face_left:face_right] = True
    return masks


def region_delta_metrics(absolute_delta: np.ndarray, masks: dict[str, np.ndarray]) -> dict[str, RegionDelta]:
    values: dict[str, RegionDelta] = {}
    pixel_changed = absolute_delta.max(axis=2) > 0
    for name, mask in masks.items():
        count = int(mask.sum())
        if count == 0:
            values[name] = RegionDelta(0.0, 0.0, 0)
            continue
        values[name] = RegionDelta(
            mean_absolute_rgb_delta=float(absolute_delta[mask].mean()),
            changed_pixel_percentage=float(pixel_changed[mask].mean() * 100),
            pixel_count=count,
        )
    return values


def replace_crop_regions(base_rgb: np.ndarray, restored_crop_rgb: np.ndarray, crop_box: BoundingBox,
                         masks: dict[str, np.ndarray], zones: Iterable[str]) -> np.ndarray:
    """Replace only declared crop-mask pixels in a copied full-frame array."""
    selected = tuple(zones)
    unknown = set(selected) - set(masks)
    if unknown:
        raise ValueError(f"Unknown diagnostic zones: {sorted(unknown)}")
    crop = base_rgb[crop_box.top:crop_box.bottom, crop_box.left:crop_box.right]
    if crop.shape != restored_crop_rgb.shape:
        raise ValueError("Restored analysis crop dimensions do not match crop placement")
    combined = np.zeros(crop.shape[:2], dtype=bool)
    for name in selected:
        combined |= masks[name]
    output = base_rgb.copy()
    destination = output[crop_box.top:crop_box.bottom, crop_box.left:crop_box.right]
    destination[combined] = restored_crop_rgb[combined]
    return output


def mask_bounds(mask: np.ndarray) -> BoundingBox | None:
    ys, xs = np.where(mask)
    if not len(xs):
        return None
    return BoundingBox(left=int(xs.min()), top=int(ys.min()), right=int(xs.max()) + 1, bottom=int(ys.max()) + 1)
