from __future__ import annotations

from typing import List, Literal
from typing import Optional

from pydantic import BaseModel, Field, model_validator


CaptionLanguage = Literal["vi", "en", "bilingual"]
VideoType = Literal["hotel_lifestyle", "character", "social_reel", "website_hero", "explainer"]
TargetEngine = Literal["veo", "kling", "runway", "seedance"]


class SourceKnowledgeRef(BaseModel):
    file: str
    dna_version: str
    hash: str


class VideoRequest(BaseModel):
    project: str
    video_type: VideoType
    topic: str
    duration_seconds: int = Field(gt=0)
    aspect_ratio: str
    platform: str
    caption_language: CaptionLanguage = "vi"
    include_character: bool = False
    target_audience: str
    source_knowledge: List[SourceKnowledgeRef] = Field(default_factory=list)
    target_engine: TargetEngine = "veo"
    alt_engines: List[TargetEngine] = Field(default_factory=list)
    validation_required: bool = True
    outfit_id: Optional[str] = None

    @model_validator(mode="after")
    def require_source_knowledge(self) -> "VideoRequest":
        if not self.source_knowledge:
            raise ValueError("VideoRequest requires source_knowledge; M06 must not invent missing Knowledge")
        return self
