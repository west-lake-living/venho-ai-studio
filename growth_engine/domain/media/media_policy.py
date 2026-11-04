from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AspectRatioPolicy(str, Enum):
    KEEP = "keep"
    PAD_4_5 = "pad_4_5"


@dataclass(frozen=True)
class TransformSpec:
    max_long_side_px: int
    max_bytes: int
    jpeg_quality: int
    aspect_ratio: AspectRatioPolicy
    background: str
    transform_version_includes: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.max_long_side_px) is not int or self.max_long_side_px <= 0:
            raise ValueError("max_long_side_px must be positive")
        if type(self.max_bytes) is not int or self.max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
        if type(self.jpeg_quality) is not int or not 1 <= self.jpeg_quality <= 100:
            raise ValueError("jpeg_quality must be between 1 and 100")
        if not isinstance(self.aspect_ratio, AspectRatioPolicy):
            raise ValueError("aspect_ratio is unsupported")
        if not self.background.strip() or not self.transform_version_includes:
            raise ValueError("background and transform version components are required")
        if any(not item.strip() for item in self.transform_version_includes):
            raise ValueError("transform version components must be non-empty")


@dataclass(frozen=True)
class MediaProfile:
    name: str
    mime: str
    spec: TransformSpec

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("profile name is required")
        if self.mime != "image/jpeg":
            raise ValueError("profile mime must be image/jpeg")


_VERSION_COMPONENTS = ("profile", "pillow_version", "pillow_heif_version")
_PROFILE_BASE = {
    "max_long_side_px": 2048,
    "max_bytes": 5_242_880,
    "jpeg_quality": 88,
    "background": "#F7F4EF",
    "transform_version_includes": _VERSION_COMPONENTS,
}

FACEBOOK_PHOTO_V1 = MediaProfile(
    name="facebook_photo_v1",
    mime="image/jpeg",
    spec=TransformSpec(aspect_ratio=AspectRatioPolicy.KEEP, **_PROFILE_BASE),
)
INSTAGRAM_PHOTO_V1 = MediaProfile(
    name="instagram_photo_v1",
    mime="image/jpeg",
    spec=TransformSpec(aspect_ratio=AspectRatioPolicy.PAD_4_5, **_PROFILE_BASE),
)
