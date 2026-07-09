from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from publishing_gateway.schemas.approval import Approval


MediaType = Literal["text", "image", "carousel", "video", "reel"]


class PublishingContent(BaseModel):
    text_prose: str
    hashtags: List[str] = Field(default_factory=list)
    media_urls: List[str] = Field(default_factory=list)
    media_type: MediaType = "text"


class PublishingSchedule(BaseModel):
    publish_now: bool = True
    scheduled_time_utc: Optional[str] = None

    @model_validator(mode="after")
    def require_time_when_scheduled(self) -> "PublishingSchedule":
        if not self.publish_now and not self.scheduled_time_utc:
            raise ValueError("scheduled_time_utc is required when publish_now=false")
        return self


class PublishingRequest(BaseModel):
    contract_version: str = "1.0"
    package_id: str
    project: str
    package_status: str
    approval: Approval
    platforms: List[str]
    content: PublishingContent
    scheduling: PublishingSchedule = Field(default_factory=PublishingSchedule)
    idempotency_key: Optional[str] = None

    @model_validator(mode="after")
    def require_platforms(self) -> "PublishingRequest":
        if not self.platforms:
            raise ValueError("platforms must not be empty")
        return self
