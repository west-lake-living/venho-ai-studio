"""Platform aspect-ratio limits, checked before a photo is ever published.

Why (2026-08-06): Instagram refuses any photo outside 4:5 (0.80) and 1.91:1
with `(36003) The aspect ratio is not supported.`, and it refuses it *inside*
Make -- after the webhook has returned 200. The first real Instagram dispatch
died that way on a 659x1440 (0.46) photo. Facebook accepts a far wider range,
so this is effectively Instagram's window, applied to everything: growth posts
the same photo to both.

Reading the file is deliberate. `daily_cycle` asks the image provider for
1024x1280 (exactly 0.80, the boundary), but nothing guarantees the bytes that
come back match the requested size -- providers normalise to their own
supported sizes. Measuring the actual artifact is the only check that cannot
be wrong, and it costs one header read.

Stdlib only (no Pillow): this project has no image library, and adding one to
read two integers out of a header is not worth the dependency.
"""

from __future__ import annotations

import struct
import math
from pathlib import Path

# Instagram's documented window for feed photos.
MIN_ASPECT_RATIO = 0.80
MAX_ASPECT_RATIO = 1.91


def read_image_size(path: Path) -> tuple[int, int] | None:
    """(width, height) of a PNG or JPEG, or None if it can't be determined.

    None means "unknown", never "invalid" -- callers must not reject a photo
    just because this could not parse it.
    """
    try:
        data = path.read_bytes()
    except OSError:
        return None

    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        width, height = struct.unpack(">II", data[16:24])
        return int(width), int(height)

    if data[:2] == b"\xff\xd8":
        # Walk the marker chain to the frame header; only SOFn carries the
        # dimensions, and it is not at a fixed offset.
        offset = 2
        while offset + 9 < len(data):
            if data[offset] != 0xFF:
                return None
            marker = data[offset + 1]
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                height, width = struct.unpack(">HH", data[offset + 5 : offset + 9])
                return int(width), int(height)
            (segment_length,) = struct.unpack(">H", data[offset + 2 : offset + 4])
            offset += 2 + segment_length
    return None


def aspect_ratio_rejection(path: Path) -> str | None:
    """Why Instagram would reject this photo, or None if it's fine.

    An unreadable/unsupported file returns None: this guard exists to catch a
    known, specific failure, not to become a second validation gate that can
    silently drop good photos.
    """
    size = read_image_size(path)
    if size is None:
        return None
    width, height = size
    if height <= 0 or width <= 0:
        return None
    ratio = width / height
    if ratio < MIN_ASPECT_RATIO or ratio > MAX_ASPECT_RATIO:
        return (
            f"aspect ratio {ratio:.2f} ({width}x{height}) is outside Instagram's "
            f"{MIN_ASPECT_RATIO:.2f}-{MAX_ASPECT_RATIO:.2f} window"
        )
    return None


def normalize_for_instagram(path: Path, *, background: str = "#F7F4EF") -> Path:
    """Pad an out-of-window image to Instagram's nearest accepted boundary.

    Generated portrait images arrive from GPT Image as 1024x1536 (2:3), even
    when the pipeline asks for 1024x1280. Padding preserves the approved image
    pixels and composition; it does not crop or regenerate the asset.
    """
    size = read_image_size(path)
    if size is None or aspect_ratio_rejection(path) is None:
        return path

    width, height = size
    ratio = width / height
    if ratio < MIN_ASPECT_RATIO:
        target_width = math.ceil(height * MIN_ASPECT_RATIO)
        target_height = height
    else:
        target_width = width
        target_height = math.ceil(width / MAX_ASPECT_RATIO)

    from PIL import Image

    with Image.open(path) as source:
        source = source.convert("RGB")
        canvas = Image.new("RGB", (target_width, target_height), background)
        canvas.paste(source, ((target_width - width) // 2, (target_height - height) // 2))
        output = path.with_name(f"{path.stem}-publish-ready.jpg")
        canvas.save(output, format="JPEG", quality=95, optimize=True)
    return output
