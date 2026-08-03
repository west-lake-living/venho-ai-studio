from __future__ import annotations

from typing import Literal
from typing import Optional

from pydantic import BaseModel, Field


ContentPackageState = Literal[
    "DRAFT",
    "GENERATING_COPY",
    "GENERATING_IMAGE",
    "VALIDATING",
    "NEEDS_REVISION",
    "READY_FOR_REVIEW",
    "UNVALIDATED",
    "APPROVED",
    "REJECTED",
    "QUEUED",
    "SCHEDULED",
    "PUBLISHING",
    "PUBLISHED",
    "PUBLISH_UNKNOWN",
    "PUBLISH_FAILED",
    "CANCELLED",
    "MEASURING",
    "MEASURED",
]


class ContentPackage(BaseModel):
    id: str
    brand_id: str
    campaign_id: str
    creative_brief_id: str
    state: ContentPackageState = "DRAFT"
    copy_version_ids: list[str] = Field(default_factory=list)
    asset_version_ids: list[str] = Field(default_factory=list)
    validation_snapshot_id: Optional[str] = None
    approval_request_id: Optional[str] = None

    def transition(self, target: ContentPackageState) -> "ContentPackage":
        allowed = {
            "DRAFT": {"GENERATING_COPY", "CANCELLED"},
            "GENERATING_COPY": {"GENERATING_IMAGE", "NEEDS_REVISION", "UNVALIDATED"},
            "GENERATING_IMAGE": {"VALIDATING", "NEEDS_REVISION", "UNVALIDATED"},
            "VALIDATING": {"NEEDS_REVISION", "READY_FOR_REVIEW", "UNVALIDATED"},
            "READY_FOR_REVIEW": {"APPROVED", "REJECTED"},
            "APPROVED": {"QUEUED", "REJECTED"},
            "QUEUED": {"SCHEDULED", "CANCELLED"},
            "SCHEDULED": {"PUBLISHING", "CANCELLED"},
            "PUBLISHING": {"PUBLISHED", "PUBLISH_UNKNOWN", "PUBLISH_FAILED", "CANCELLED"},
            "PUBLISHED": {"MEASURING"},
            "MEASURING": {"MEASURED"},
        }
        if target not in allowed.get(self.state, set()):
            raise ValueError(f"Invalid ContentPackage transition: {self.state} -> {target}")
        return self.model_copy(update={"state": target})

    def assert_approvable(self) -> None:
        if self.state != "READY_FOR_REVIEW":
            raise ValueError("Only READY_FOR_REVIEW packages can be approved")
        if not self.copy_version_ids or not self.asset_version_ids or not self.validation_snapshot_id:
            raise ValueError("Approval requires copy, asset, and validation exact versions")
