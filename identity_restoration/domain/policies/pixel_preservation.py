from __future__ import annotations

import hashlib
from dataclasses import dataclass
from io import BytesIO

import numpy as np
from PIL import Image, ImageChops

from image_studio_runtime.action_composite.regression_guard import protected_region

# Extract, don't recreate (patch v2.1 §2.3): the pixel-preservation guard
# already exists and is verified (image_studio_runtime/action_composite/
# regression_guard.py). This module imports its pure comparison primitive
# rather than duplicating the pixel math, and adds the PixelLockReport shape
# the new Port/use-case layer expects (v2.0 PHẦN 4.2).
#
# A beautiful face that changes locked pixels is a HARD FAIL: it means the
# worker regenerated body/outfit/background, i.e. it produced a different
# image, not a restoration.


@dataclass(frozen=True)
class PixelLockReport:
    passed: bool
    mutated_pixel_count: int
    editable_region_hash: str


def assert_pixels_preserved(*, before_canvas: bytes, after_canvas: bytes, editable_mask: bytes,
                            tolerance: int = 0) -> PixelLockReport:
    """Byte-exact by default (tolerance=0). Only widen if an ADR records why."""
    before = Image.open(BytesIO(before_canvas)).convert("RGBA")
    after = Image.open(BytesIO(after_canvas)).convert("RGBA")
    mask = Image.open(BytesIO(editable_mask)).convert("L")
    if before.size != after.size or mask.size != before.size:
        raise ValueError("before, after and mask must have identical dimensions")

    diff = ImageChops.difference(before, after).convert("L")
    locked = protected_region(mask, epsilon=tolerance)
    violation = ImageChops.multiply(diff, locked)
    mutated = int(np.count_nonzero(np.asarray(violation)))
    editable_hash = hashlib.sha256(mask.tobytes()).hexdigest()
    return PixelLockReport(passed=mutated == 0, mutated_pixel_count=mutated, editable_region_hash=editable_hash)
