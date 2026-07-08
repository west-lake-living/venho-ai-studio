from __future__ import annotations

import base64
import hashlib
from pathlib import Path
from typing import Iterator

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

_EXIF_TAGS_KEEP = {
    "DateTimeOriginal", "DateTime", "Make", "Model",
    "ExposureTime", "FNumber", "ISOSpeedRatings",
    "FocalLength", "Software",
}


def read_exif(path: Path) -> dict:
    """Extract useful EXIF fields from image. Returns {} if unavailable."""
    try:
        from PIL import Image, ExifTags
        with Image.open(path) as img:
            raw = img._getexif()
            if not raw:
                return {}
            result = {}
            for tag_id, value in raw.items():
                name = ExifTags.TAGS.get(tag_id)
                if name in _EXIF_TAGS_KEEP:
                    result[name] = str(value)
            return result
    except Exception:
        return {}


def load_images(folder: Path) -> list[Path]:
    """Return all supported image paths, recursively sorted."""
    paths = [
        p for p in sorted(folder.rglob("*"))
        if p.suffix.lower() in SUPPORTED_EXTENSIONS and p.is_file()
    ]
    return paths


def image_to_base64(path: Path) -> tuple[str, str]:
    """Return (base64_data, media_type) for an image file."""
    suffix = path.suffix.lower()
    media_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    media_type = media_type_map.get(suffix, "image/jpeg")
    data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
    return data, media_type


def image_hash(path: Path) -> str:
    """SHA256 hash of image file contents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()
