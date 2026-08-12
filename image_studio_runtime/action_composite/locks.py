from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .models import BoundingBox, FaceGeometry


@dataclass(frozen=True)
class GeometryLock:
    """Immutable geometry contract carried across identity restoration."""

    geometry: FaceGeometry
    bbox_tolerance_px: int = 0
    angle_tolerance_deg: float = 2.0

    def validate(self, candidate: FaceGeometry) -> tuple[bool, list[str]]:
        failures: list[str] = []
        if not self._bbox_close(self.geometry.face_bbox, candidate.face_bbox):
            failures.append("face_bbox_changed")
        if not self._bbox_close(self.geometry.head_bbox, candidate.head_bbox):
            failures.append("head_bbox_changed")
        for name in ("yaw", "pitch", "roll"):
            if abs(getattr(self.geometry, name) - getattr(candidate, name)) > self.angle_tolerance_deg:
                failures.append(f"{name}_changed")
        return not failures, failures

    def as_manifest(self) -> dict:
        return {"geometry": self.geometry.model_dump(), "bbox_tolerance_px": self.bbox_tolerance_px,
                "angle_tolerance_deg": self.angle_tolerance_deg}

    def _bbox_close(self, expected: BoundingBox, candidate: BoundingBox) -> bool:
        tolerance = self.bbox_tolerance_px
        return all(abs(getattr(expected, key) - getattr(candidate, key)) <= tolerance
                   for key in ("left", "top", "right", "bottom"))


def enforce_geometry_lock(lock: GeometryLock, candidate: Optional[FaceGeometry]) -> None:
    if candidate is None:
        return
    valid, failures = lock.validate(candidate)
    if not valid:
        raise ValueError("Geometry lock violation: " + ", ".join(failures))
