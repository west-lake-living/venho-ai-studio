from __future__ import annotations

from io import BytesIO
from typing import Callable

from PIL import Image

from publishing_gateway.image_constraints import MAX_ASPECT_RATIO, MIN_ASPECT_RATIO


MAX_IMAGE_BYTES = 5 * 1024 * 1024
_EXIF_ORIENTATION_TAG = 274


def check_output_image(url: str, fetch: Callable[[str], bytes]) -> list[str]:
    """Validate the exact JPEG bytes before a legacy Make dispatch.

    ``fetch`` is injected so callers control network policy and tests remain offline.
    """
    if not url.strip():
        return ["OUTPUT_IMAGE_FETCH_FAILED"]
    try:
        data = fetch(url)
    except Exception:
        return ["OUTPUT_IMAGE_FETCH_FAILED"]
    if not isinstance(data, bytes):
        return ["OUTPUT_IMAGE_FETCH_FAILED"]
    if len(data) > MAX_IMAGE_BYTES:
        return ["OUTPUT_IMAGE_TOO_LARGE"]
    if not data.startswith(b"\xff\xd8\xff"):
        return ["OUTPUT_IMAGE_NOT_JPEG"]

    try:
        with Image.open(BytesIO(data)) as image:
            if image.format != "JPEG":
                return ["OUTPUT_IMAGE_NOT_JPEG"]
            image.load()
            width, height = image.size
            orientation = image.getexif().get(_EXIF_ORIENTATION_TAG)
    except Exception:
        return ["OUTPUT_IMAGE_DECODE_FAILED"]

    if orientation not in (None, 1):
        return ["OUTPUT_IMAGE_EXIF_ORIENTATION"]
    if width <= 0 or height <= 0:
        return ["OUTPUT_IMAGE_DECODE_FAILED"]
    ratio = width / height
    if ratio < MIN_ASPECT_RATIO or ratio > MAX_ASPECT_RATIO:
        return ["OUTPUT_IMAGE_ASPECT_RATIO"]
    return []
