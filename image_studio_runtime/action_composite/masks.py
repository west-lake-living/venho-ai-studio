from __future__ import annotations

from PIL import Image, ImageDraw, ImageFilter

from .models import BoundingBox


def face_mask(size: tuple[int, int], bbox: BoundingBox, *, feather: int = 8) -> Image.Image:
    """Create a soft elliptical face mask; pixels outside it stay untouched."""
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((bbox.left, bbox.top, bbox.right, bbox.bottom), fill=255)
    return mask.filter(ImageFilter.GaussianBlur(radius=max(0, feather)))


def crop_for_identity(image: Image.Image, bbox: BoundingBox, *, scale: float = 2.5) -> tuple[Image.Image, BoundingBox]:
    # A scale below 1 turns the padding negative and inverts the box; the crop
    # exists to give the restorer more context, never less.
    if scale < 1.0:
        raise ValueError("crop scale must be >= 1.0")
    crop_box = bbox.padded((scale - 1) / 2, image.width, image.height)
    return image.crop((crop_box.left, crop_box.top, crop_box.right, crop_box.bottom)), crop_box
