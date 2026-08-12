from __future__ import annotations

from pathlib import Path
from typing import Optional, Protocol

from PIL import Image

from .models import BoundingBox, FaceGeometry


class FaceDetector(Protocol):
    def detect(self, image: Image.Image, requested_bbox: Optional[BoundingBox] = None) -> FaceGeometry: ...


class BBoxFaceDetector:
    """Deterministic detector adapter for POC and external detector handoff.

    Production detectors can implement the same protocol. A bbox is mandatory
    unless the image manifest provides ``face_bbox``; this prevents silently
    repairing the wrong region.
    """

    def detect(self, image: Image.Image, requested_bbox: Optional[BoundingBox] = None) -> FaceGeometry:
        bbox = requested_bbox
        if bbox is None:
            raise ValueError("face_bbox is required until a production detector adapter is configured")
        if bbox.right > image.width or bbox.bottom > image.height:
            raise ValueError("face_bbox is outside base image bounds")
        return FaceGeometry(face_bbox=bbox, head_bbox=bbox.padded(0.55, image.width, image.height),
                            face_scale=bbox.width / image.width)


def load_image(path: str | Path) -> Image.Image:
    image = Image.open(path).convert("RGBA")
    if image.width < 64 or image.height < 64:
        raise ValueError("base image is too small for face restoration")
    return image
