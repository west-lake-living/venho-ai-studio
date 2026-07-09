from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

PromptType = Literal["image", "video", "content", "seo"]
TargetLanguage = Literal["en", "vi", "bilingual"]
ValidationStatus = Literal["pass", "fail", "pending"]


class SourceKnowledgeEntry(BaseModel):
    """One DNA JSON file (Module 01 output) that a prompt was built from."""

    file: str
    dna_version: str
    dna_contract_version: str
    hash: str


class TemplateInfo(BaseModel):
    name: str
    template_version: str


class RequiredDnaItem(BaseModel):
    """An invariant (or forbidden rule) that MUST be reflected in final_prompt (§7.3)."""

    key: str
    value: str


class AllowedVariationItem(BaseModel):
    """DNA `variable` mapped to prompt `allowed_variations` (§3.4)."""

    key: str
    value_range: List[str]


class AllowedImperfectionItem(BaseModel):
    value: str
    source: str


class ForbiddenItem(BaseModel):
    rule: str
    source: str


class OptimizerInfo(BaseModel):
    used: bool
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None


class ValidationBlock(BaseModel):
    structural: ValidationStatus = "pending"
    faithfulness: ValidationStatus = "pending"
