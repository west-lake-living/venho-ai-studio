from __future__ import annotations

import hashlib
from dataclasses import dataclass
from io import BytesIO

from PIL import Image

from .errors import RestorationError
from .value_objects import RestorationParams

# PHẦN 4.1 of the v2.0 plan. Pure value objects: bytes and numbers in, bytes
# and numbers out. Decoding PNG bytes already held in memory (BytesIO) is not
# disk I/O and stays here; reading files, env vars or the wall clock does not.


@dataclass(frozen=True)
class A2Authority:
    """The single identity source of Linh An. Immutable for the job's lifetime."""

    image_bytes: bytes
    sha256: str

    def verify(self, expected_sha256: str) -> None:
        if self.sha256 != expected_sha256:
            raise RestorationError(
                "ERR_GW_A2_HASH_MISMATCH",
                "A2 authority sha256 does not match the pinned reference; refusing to spend "
                "any resource before the identity source is verified.",
                retryable=False,
            )

    @staticmethod
    def from_bytes(data: bytes) -> "A2Authority":
        return A2Authority(image_bytes=data, sha256=hashlib.sha256(data).hexdigest())


@dataclass(frozen=True)
class CropTransform:
    """Affine crop <-> canvas mapping. Must be invertible — round-trip tested."""

    source_x: int
    source_y: int
    source_w: int
    source_h: int
    target_size: int
    rotation_deg: float = 0.0

    def to_box(self) -> tuple[int, int, int, int]:
        return (self.source_x, self.source_y, self.source_x + self.source_w, self.source_y + self.source_h)

    @staticmethod
    def from_box(left: int, top: int, right: int, bottom: int, target_size: int) -> "CropTransform":
        return CropTransform(source_x=left, source_y=top, source_w=right - left, source_h=bottom - top,
                              target_size=target_size)

    def round_trips(self) -> bool:
        """CropTransform.from_box(*self.to_box(), self.target_size) == self."""
        left, top, right, bottom = self.to_box()
        return CropTransform.from_box(left, top, right, bottom, self.target_size) == self


@dataclass(frozen=True)
class MaskSet:
    """Hierarchical mask. ``editable`` is the ONLY region pixels may change in."""

    editable: bytes
    feather: bytes
    version: str


@dataclass(frozen=True)
class RestorationParamsRequest:
    """Alias kept for readability at call sites; identical to RestorationParams."""

    params: RestorationParams


@dataclass(frozen=True)
class RestorationRequest:
    run_id: str
    attempt_id: str
    crop_png: bytes
    mask: MaskSet
    a2: A2Authority
    workflow_id: str
    seed: int
    params: RestorationParams


@dataclass(frozen=True)
class RestoredCrop:
    png_bytes: bytes
    width: int
    height: int

    def assert_geometry_matches(self, request: "RestorationRequest") -> None:
        expected = Image.open(BytesIO(request.crop_png)).size
        if (self.width, self.height) != expected:
            raise RestorationError(
                "ERR_GW_GEOMETRY_MISMATCH",
                f"Restored crop is {self.width}x{self.height}, expected {expected[0]}x{expected[1]}. "
                "Never auto-resize: that would hide a workflow bug and corrupt the pixel lock.",
                retryable=False,
            )

    @staticmethod
    def from_png_bytes(data: bytes) -> "RestoredCrop":
        width, height = Image.open(BytesIO(data)).size
        return RestoredCrop(png_bytes=data, width=width, height=height)
