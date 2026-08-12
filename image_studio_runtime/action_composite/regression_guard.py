from __future__ import annotations

from typing import Optional

from PIL import Image, ImageChops


def protected_region(mask: Image.Image, *, epsilon: int = 0) -> Image.Image:
    """Return the region that a repair must leave untouched.

    A feathered mask blends over its own edge, so "outside the bbox" is not the
    same as "not repaired". Only pixels whose mask value is at or below
    ``epsilon`` are genuinely locked; the feather band belongs to the repair.
    """
    return mask.convert("L").point(lambda value: 255 if value <= epsilon else 0)


def unchanged_outside_mask(before: Image.Image, after: Image.Image, mask: Image.Image,
                           *, epsilon: int = 0) -> bool:
    """Return true only when repair leaves every locked pixel byte-identical."""
    if before.size != after.size or mask.size != before.size:
        raise ValueError("before, after and mask must have identical dimensions")
    # Compare every channel: an RGB-only mutation leaves alpha untouched, so an
    # alpha-only diff would report a clean run for a fully repainted background.
    diff = ImageChops.difference(before.convert("RGBA"), after.convert("RGBA")).convert("L")
    return ImageChops.multiply(diff, protected_region(mask, epsilon=epsilon)).getbbox() is None


def assert_no_regression(before: Image.Image, after: Image.Image, mask: Image.Image,
                         *, epsilon: int = 0) -> None:
    if not unchanged_outside_mask(before, after, mask, epsilon=epsilon):
        raise ValueError("Regression guard failed: pixels outside repair mask changed")


def compare_locked_region(before: Image.Image, after: Image.Image, locked_mask: Optional[Image.Image] = None) -> bool:
    """Convenience check for a locked region; without a mask the whole image is locked."""
    if locked_mask is None:
        return before.convert("RGBA").tobytes() == after.convert("RGBA").tobytes()
    return unchanged_outside_mask(before, after, ImageChops.invert(locked_mask.convert("L")))
