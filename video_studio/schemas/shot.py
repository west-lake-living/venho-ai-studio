from __future__ import annotations

from pydantic import BaseModel, Field


class Shot(BaseModel):
    scene_number: int = Field(gt=0)
    angle: str
    camera_movement: str
    motion_note: str
    lighting_note: str

