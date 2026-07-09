from __future__ import annotations

from typing import List

from pydantic import BaseModel

from prompt_studio.schemas.base import (
    AllowedImperfectionItem,
    AllowedVariationItem,
    ForbiddenItem,
    OptimizerInfo,
    PromptType,
    RequiredDnaItem,
    SourceKnowledgeEntry,
    TargetLanguage,
    TemplateInfo,
    ValidationBlock,
)


class PromptContractBase(BaseModel):
    """Shared shape for every prompt type (§7.1). Type-specific fields (negative_prompt vs
    restrictions) live in schemas/{image,video,content,seo}_prompt.py subclasses."""

    contract_version: str
    module: str = "prompt_studio"
    project: str
    prompt_type: PromptType
    prompt_id: str
    prompt_version: str
    generated_at: str
    source_knowledge: List[SourceKnowledgeEntry]
    template: TemplateInfo
    task_brief: str
    target_language: TargetLanguage
    required_dna: List[RequiredDnaItem]
    allowed_variations: List[AllowedVariationItem] = []
    allowed_imperfections: List[AllowedImperfectionItem] = []
    forbidden: List[ForbiddenItem] = []
    final_prompt: str
    optimizer: OptimizerInfo
    validation: ValidationBlock
    notes: List[str] = []
