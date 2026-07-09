from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from content_studio.schemas.content_request import SourceKnowledgeRef, TargetLanguage


class SourcePromptRef(BaseModel):
    file: Optional[str] = None
    prompt_id: str
    prompt_version: str


class GeneratorInfo(BaseModel):
    provider: str = "mock"
    model: str = "deterministic-social-builder"
    temperature: float = 0.6


class ValidationInfo(BaseModel):
    required: bool = True
    status: Literal["pending", "pass", "warning", "fail", "not_available"] = "pending"
    report_file: Optional[str] = None
    notes: List[str] = Field(default_factory=list)


class ContentOutput(BaseModel):
    contract_version: str = "1.0"
    module: str = "content_studio"
    project: str
    content_type: str
    target_language: TargetLanguage
    generated_at: str
    source_knowledge: List[SourceKnowledgeRef]
    source_prompt: SourcePromptRef
    generator: GeneratorInfo
    title: str
    hook: str
    body: str
    cta: str
    hashtags: List[str] = Field(default_factory=list)
    visual_note: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: Literal["draft"] = "draft"
    validation: ValidationInfo = Field(default_factory=ValidationInfo)
