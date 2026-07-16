from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from video_studio.schemas.engine_prompt import EnginePrompt
from video_studio.schemas.shot import Shot
from video_studio.schemas.storyboard import ContinuityCheck, DurationCheck, StoryboardScene
from video_studio.schemas.video_request import SourceKnowledgeRef
from shared.contract_refs import ContractRefs


class Concept(BaseModel):
    title: str
    objective: str
    tone: str


class TextFromContent(BaseModel):
    caption: Optional[str] = None
    hook: Optional[str] = None
    voiceover: Optional[str] = None
    cta: Optional[str] = None
    caption_language: str
    source_file: Optional[str] = None


class ValidationInfo(BaseModel):
    scope: Literal["pre_render"] = "pre_render"
    required: bool = True
    status: Literal["pending", "pass", "warning", "fail", "not_available"] = "pending"
    reports: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class VideoPackage(BaseModel):
    contract_version: str = "1.0"
    module: str = "video_studio"
    project: str
    video_type: str
    duration_seconds: int
    aspect_ratio: str
    platform: str
    target_engine: str
    alt_engines: List[str] = Field(default_factory=list)
    generated_at: str
    source_knowledge: List[SourceKnowledgeRef]
    continuity_keys: List[str] = Field(default_factory=list)
    contract_refs: Optional[ContractRefs] = None
    concept: Concept
    storyboard: List[StoryboardScene]
    shot_list: List[Shot]
    duration_check: DurationCheck
    continuity_check: ContinuityCheck
    text_from_content: TextFromContent
    engine_prompt_full: str
    engine_prompts: List[EnginePrompt] = Field(default_factory=list)
    motion_negative_prompt: str
    character_rules: Dict[str, Any] = Field(default_factory=dict)
    camera_motion_rules: Dict[str, Any] = Field(default_factory=dict)
    validation: ValidationInfo = Field(default_factory=ValidationInfo)
    status: Literal["draft"] = "draft"
