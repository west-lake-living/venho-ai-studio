from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

TargetLanguage = Literal["vi", "en", "bilingual"]
ContentType = Literal[
    "facebook_post",
    "instagram_post",
    "threads_post",
    "tiktok_caption",
    "blog",
    "website",
    "ota",
    "email",
    "faq",
]
ContentLength = Literal["short", "medium", "long"]


class SourceKnowledgeRef(BaseModel):
    file: str
    dna_version: str
    hash: str


class ContentRequest(BaseModel):
    project: str
    content_type: ContentType
    topic: str
    target_audience: str
    content_pillar: str
    tone: str
    length: ContentLength = "medium"
    target_language: TargetLanguage = "vi"
    cta_type: str = "booking_soft"
    keyword: Optional[str] = None
    month: Optional[str] = None
    channels: List[str] = Field(default_factory=list)
    source_knowledge: List[SourceKnowledgeRef] = Field(default_factory=list)
    validation_required: bool = True
    subject: Optional[str] = None
    outfit_id: Optional[str] = None

    @property
    def platform(self) -> str:
        return self.content_type.removesuffix("_post").removesuffix("_caption")
