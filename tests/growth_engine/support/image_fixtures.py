from __future__ import annotations

import struct
import zlib
from io import BytesIO

from PIL import Image, ImageDraw


def make_orientation_jpeg(orientation: int) -> bytes:
    image = Image.new("RGB", (80, 60), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 38, 28), fill=(235, 30, 30))
    draw.rectangle((41, 0, 79, 28), fill=(30, 210, 30))
    draw.rectangle((0, 31, 38, 59), fill=(30, 30, 230))
    draw.rectangle((41, 31, 79, 59), fill=(235, 210, 20))
    exif = Image.Exif()
    exif[274] = orientation
    return _save(image, "JPEG", quality=100, subsampling=0, exif=exif)


def make_alpha_png() -> bytes:
    image = Image.new("RGBA", (40, 20), (0, 0, 0, 0))
    ImageDraw.Draw(image).rectangle((10, 5, 30, 15), fill=(255, 0, 0, 128))
    return _save(image, "PNG")


def make_truncated_jpeg() -> bytes:
    return make_orientation_jpeg(1)[:-2]


def make_html_with_jpg_extension() -> bytes:
    return b"<html><body>not an image</body></html>"


def make_pixel_bomb_png(width: int = 20_000, height: int = 20_000) -> bytes:
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", zlib.compress(b""))
        + _png_chunk(b"IEND", b"")
    )


def make_heic() -> bytes | None:
    try:
        import pillow_heif

        pillow_heif.register_heif_opener()
        image = Image.new("RGB", (64, 48), (35, 130, 180))
        encoded = pillow_heif.from_pillow(image)
        output = BytesIO()
        encoded.save(output, quality=80)
        return output.getvalue()
    except (ImportError, OSError, RuntimeError, ValueError):
        return None


def _save(image: Image.Image, format_name: str, **options: object) -> bytes:
    output = BytesIO()
    image.save(output, format=format_name, **options)
    return output.getvalue()


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    checksum = zlib.crc32(kind + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", checksum)
