from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class ScenePromptRef(BaseModel):
    source: str = "module_02"
    prompt_id: str
    prompt_version: str
    file: str | None = None


class StoryboardScene(BaseModel):
    scene_number: int = Field(gt=0)
    duration_seconds: int = Field(gt=0)
    description: str
    camera_movement: str
    visual_dna_required: List[str] = Field(default_factory=list)
    scene_prompt_ref: ScenePromptRef | None = None
    engine_prompt: str | None = None
    forbidden: List[dict] = Field(default_factory=list)


class DurationCheck(BaseModel):
    sum_scenes: int
    target: int
    ok: bool


class ContinuityCheck(BaseModel):
    all_scenes_have_keys: bool
    missing_by_scene: dict[int, List[str]] = Field(default_factory=dict)

