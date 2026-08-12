from __future__ import annotations

import base64
import hashlib
import subprocess
from pathlib import Path
from typing import Iterator

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".avif"}

# Converted AVIF frames live here, never next to the source images: writing into
# the user's photo folder would mutate the input of a read, and a pre-existing
# sibling `.jpg` is a *different* photo, not a cached conversion of this one.
AVIF_CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / ".cache" / "avif"


def _normalize_avif(path: Path) -> Path:
    """Return a JPEG the vision API can read, converting AVIF on first use.

    Keyed by content hash, so re-running Mode A/B/C reuses the conversion and an
    edited source image is never served from a stale cache entry.
    """
    if path.suffix.lower() != ".avif":
        return path
    output = AVIF_CACHE_DIR / f"{image_hash(path)}.jpg"
    if output.exists():
        return output
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image

        with Image.open(path) as image:
            image.convert("RGB").save(output, format="JPEG", quality=95)
        return output
    except Exception:
        return _convert_avif_with_sips(path, output)


def _convert_avif_with_sips(path: Path, output: Path) -> Path:
    """Fallback for Pillow builds without AVIF support (macOS only)."""
    try:
        subprocess.run(
            ["sips", "-s", "format", "jpeg", str(path), "--out", str(output)],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(
            f"Cannot read AVIF image {path.name}: Pillow has no AVIF support and "
            "JPEG conversion via sips failed."
        ) from exc
    return output

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
    # Never de-duplicate the result: an AVIF and a JPEG sharing a stem are two
    # separate photos, and silently dropping one changes the image count a Mode B
    # run is validated against.
    return [
        _normalize_avif(path)
        for path in sorted(folder.rglob("*"))
        if path.suffix.lower() in SUPPORTED_EXTENSIONS and path.is_file()
    ]


def image_to_base64(path: Path) -> tuple[str, str]:
    """Return (base64_data, media_type) for an image file."""
    suffix = path.suffix.lower()
    media_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".avif": "image/avif",
    }
    media_type = media_type_map.get(suffix, "image/jpeg")
    data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
    return data, media_type


def image_hash(path: Path) -> str:
    """SHA256 hash of image file contents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()
