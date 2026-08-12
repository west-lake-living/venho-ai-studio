from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ReproducibilityMetadata(BaseModel):
    seed: Optional[int] = None
    model: Optional[str] = None
    model_hash: Optional[str] = None
    workflow_version: str
    node_versions: Dict[str, str] = Field(default_factory=dict)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    mask_parameters: Dict[str, Any] = Field(default_factory=dict)
    identity_weight: Optional[float] = None

    def as_manifest(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)
