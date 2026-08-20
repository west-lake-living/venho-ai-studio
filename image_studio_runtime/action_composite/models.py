from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field, field_validator


class CompositeState(str, Enum):
    INIT = "INIT"
    GENERATE_ACTION = "GENERATE_ACTION"
    SELECT_CANDIDATE = "SELECT_CANDIDATE"
    ANALYZE_GEOMETRY = "ANALYZE_GEOMETRY"
    RESTORE_FACE = "RESTORE_FACE"
    VALIDATE_FACE = "VALIDATE_FACE"
    VALIDATE_GLOBAL = "VALIDATE_GLOBAL"
    REPAIR_FACE = "REPAIR_FACE"
    SELECTIVE_REPAIR = "SELECTIVE_REPAIR"
    FINALIZE = "FINALIZE"
    FAILED = "FAILED"


class BoundingBox(BaseModel):
    left: int = Field(ge=0)
    top: int = Field(ge=0)
    right: int = Field(gt=0)
    bottom: int = Field(gt=0)

    @field_validator("right")
    @classmethod
    def right_after_left(cls, value: int, info: Any) -> int:
        if "left" in info.data and value <= info.data["left"]:
            raise ValueError("right must be greater than left")
        return value

    @field_validator("bottom")
    @classmethod
    def bottom_after_top(cls, value: int, info: Any) -> int:
        if "top" in info.data and value <= info.data["top"]:
            raise ValueError("bottom must be greater than top")
        return value

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    def padded(self, padding: float, width: int, height: int) -> "BoundingBox":
        px = round(self.width * padding)
        py = round(self.height * padding)
        return BoundingBox(left=max(0, self.left - px), top=max(0, self.top - py),
                           right=min(width, self.right + px), bottom=min(height, self.bottom + py))


class FaceGeometry(BaseModel):
    face_bbox: BoundingBox
    head_bbox: BoundingBox
    yaw: float = 0.0
    pitch: float = 0.0
    roll: float = 0.0
    face_scale: float = Field(gt=0)
    eye_line: Optional[float] = None
    nose_axis: Optional[float] = None
    mouth_line: Optional[float] = None
    jaw_contour: List[Tuple[float, float]] = Field(default_factory=list)
    hairline_boundary: List[Tuple[float, float]] = Field(default_factory=list)
    neck_boundary: List[Tuple[float, float]] = Field(default_factory=list)


class ActionCompositeJob(BaseModel):
    job_id: str
    base_image: str
    identity_reference: str
    identity_authority: Literal["A2_FRONT"] = "A2_FRONT"
    face_bbox: Optional[BoundingBox] = None
    workflow_version: str = "face_restore_v1"
    provider: str = "comfyui"
    scene_provider: str = "nano_banana"
    candidate_id: Optional[str] = None
    identity_reference_sha256: Optional[str] = Field(default=None, min_length=64, max_length=64)
    mask_version: str = "hierarchical_face_v1"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("identity_reference")
    @classmethod
    def require_a2_reference(cls, value: str) -> str:
        # Match the filename only: a candidate image parked in a folder named
        # "A2_benchmarks/" is still not the identity authority (plan §4.1).
        stem = Path(value).stem.upper().replace("_", "-").replace(" ", "-")
        if "A2-FRONT" not in stem:
            raise ValueError("Action Composite requires A2-FRONT as the sole identity authority")
        return value

    @field_validator("identity_reference_sha256")
    @classmethod
    def valid_sha256(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and any(char not in "0123456789abcdefABCDEF" for char in value):
            raise ValueError("identity_reference_sha256 must be a hexadecimal SHA-256")
        return value.lower() if value else value


class RegionalQC(BaseModel):
    identity_score: Optional[float] = Field(default=None, ge=0, le=100)
    eyes_brows_score: Optional[float] = Field(default=None, ge=0, le=100)
    geometry_score: Optional[float] = Field(default=None, ge=0, le=100)
    anatomy_score: Optional[float] = Field(default=None, ge=0, le=100)
    outfit_score: Optional[float] = Field(default=None, ge=0, le=100)
    environment_score: Optional[float] = Field(default=None, ge=0, le=100)
    global_score: Optional[float] = Field(default=None, ge=0, le=100)
    pixel_preservation: bool
    status: Literal["PASS", "FAIL", "UNVALIDATED"]
    failures: list[str] = Field(default_factory=list)


class CompositeResult(BaseModel):
    job_id: str
    state: CompositeState
    output_path: str
    geometry: FaceGeometry
    qc: RegionalQC
    metadata: dict[str, Any] = Field(default_factory=dict)
