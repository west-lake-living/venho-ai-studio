from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from prompt_studio.builders.content_prompt_builder import build_content_prompt
from prompt_studio.knowledge_reader import DnaReadError, read_dna
from prompt_studio.prompt_store import save_prompt
from prompt_studio.schemas.content_prompt import ContentPromptContract

from content_studio.schemas.content_request import ContentRequest


class MissingKnowledgeError(Exception):
    """Module 02 cannot build a content prompt because the source DNA is missing."""


@dataclass
class PromptBridgeResult:
    contract: ContentPromptContract
    json_path: Path
    markdown_path: Path


def slugify(value: str) -> str:
    lowered = value.lower()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    return lowered.strip("-") or "content"


def _knowledge_path(request: ContentRequest, data_root: Path) -> Path:
    if request.source_knowledge:
        raw = Path(request.source_knowledge[0].file)
        if raw.is_absolute():
            return raw
        if raw.exists():
            return raw
        return data_root / request.project / "knowledge" / raw.name

    if request.subject:
        subject = request.subject.upper()
        return data_root / request.project / "knowledge" / f"VENHO_HOTEL_{subject}_DNA.json"

    raise MissingKnowledgeError("ContentRequest must include source_knowledge or subject")


def build_task_brief(request: ContentRequest) -> str:
    return (
        f"Create a {request.content_type} draft about '{request.topic}' for "
        f"{request.target_audience}. Content pillar: {request.content_pillar}. "
        f"Tone: {request.tone}. Length: {request.length}. CTA type: {request.cta_type}."
    )


def build_content_prompt_for_request(
    request: ContentRequest,
    *,
    data_root: Path = Path("data/projects"),
    prompts_root: Optional[Path] = None,
) -> PromptBridgeResult:
    dna_path = _knowledge_path(request, data_root)
    try:
        dna = read_dna(dna_path)
    except DnaReadError as exc:
        raise MissingKnowledgeError(str(exc)) from exc

    brief_slug = slugify(f"{request.platform}-{request.topic}")[:80]
    contract = build_content_prompt(
        dna=dna,
        task_brief=build_task_brief(request),
        brief_slug=brief_slug,
        target_language=request.target_language,
        outfit_id=request.outfit_id,
        character_id="linh_an" if request.outfit_id else None,
    )
    paths = save_prompt(contract, root=prompts_root or data_root)
    return PromptBridgeResult(contract=contract, json_path=paths.json, markdown_path=paths.markdown)
