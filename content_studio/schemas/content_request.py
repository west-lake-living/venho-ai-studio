from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

TargetLanguage = Literal["vi", "en", "bilingual"]
ContentType = Literal[
    "facebook_post",
    "instagram_post",
    "threads_post",
    "tiktok_caption",
    "zalo_post",
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
    lane: str = "daily"
    verified_events: List[Dict[str, Any]] = Field(default_factory=list)
    dna_subject: Optional[str] = None
    # 2026-08-13 diversity fix: approved local facts (Wednesday's
    # local_discovery lane -- see growth_orchestrator.application.local_intel)
    # and recent post topics/titles (any lane), both optional and both
    # empty by default so every existing caller is unaffected.
    research_facts: List[Dict[str, Any]] = Field(default_factory=list)
    recent_topics: List[str] = Field(default_factory=list)
    # Which system-prompt rule block a lane gets (see
    # content_studio.generators.social_prompts.select_system_prompt):
    # "default" | "west_lake_life" | "local_discovery" | "weekend_events".
    # Defaults to "default" so any caller that never sets it keeps getting
    # the base SYSTEM_PROMPT/WEST_LAKE_SYSTEM_PROMPT selection logic that
    # existed before this field (dna_subject/lane based).
    prompt_rules: str = "default"

    @property
    def platform(self) -> str:
        return self.content_type.removesuffix("_post").removesuffix("_caption")
