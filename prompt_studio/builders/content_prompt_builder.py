"""Content Prompt Builder (§16 Step 11) — deterministic. No visual negative_prompt; tone/
claim restrictions instead (§5.3). target_language drives the language of the CONTENT
itself; the instructions in final_prompt stay English (§10, hard rule)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from prompt_studio.knowledge_reader import KnowledgeDna
from prompt_studio.prompt_rules import load_prompt_rules
from prompt_studio.restrictions import merge_restrictions
from prompt_studio.schemas.base import (
    AllowedImperfectionItem,
    AllowedVariationItem,
    OptimizerInfo,
    RequiredDnaItem,
    TargetLanguage,
    TemplateInfo,
    ValidationBlock,
)
from prompt_studio.schemas.content_prompt import ContentPromptContract
from prompt_studio.template_loader import PromptTemplate, load_template

_LANGUAGE_LABEL = {
    "vi": "Vietnamese",
    "en": "English",
    "bilingual": "both Vietnamese and English",
}


def render_final_prompt(
    task_brief: str,
    target_language: TargetLanguage,
    prompt_rules: Dict[str, Any],
    required_dna: List[RequiredDnaItem],
    allowed_variations: List[AllowedVariationItem],
) -> str:
    lines = [task_brief.strip(), "", f"Write the content in {_LANGUAGE_LABEL[target_language]}.", ""]

    lines.append(f"Audience: {prompt_rules['audience']}")
    lines.append(f"Tone: {prompt_rules['tone']}")
    lines.append("")

    lines.append("Brand DNA:")
    lines.extend(f"- {line}" for line in prompt_rules.get("brand_dna", []))
    lines.append("")

    if required_dna:
        lines.append("Required facts (must appear, do not alter):")
        lines.extend(f"- {item.key}: {item.value}" for item in required_dna)
        lines.append("")

    if allowed_variations:
        lines.append("Flexible details (any one of the listed options is acceptable):")
        lines.extend(f"- {item.key}: {' / '.join(item.value_range)}" for item in allowed_variations)
        lines.append("")

    lines.append(f"Call-to-action: {prompt_rules['cta_rule']}")

    return "\n".join(lines).strip()


def build_content_prompt(
    dna: KnowledgeDna,
    task_brief: str,
    brief_slug: str,
    target_language: Optional[TargetLanguage] = None,
    prompt_rules: Optional[Dict[str, Any]] = None,
    template: Optional[PromptTemplate] = None,
    prompt_version: str = "1.0",
    contract_version: str = "1.0",
    generated_at: Optional[str] = None,
) -> ContentPromptContract:
    """Build a content Prompt JSON from one brand/location DNA + a brief (§7.1, §5.3)."""
    template = template or load_template("content")
    generated_at = generated_at or datetime.now(timezone.utc).isoformat()
    prompt_rules = prompt_rules or load_prompt_rules(dna.project)
    target_language = target_language or prompt_rules["default_target_language"]

    required_dna = list(dna.required_dna)
    allowed_variations = list(dna.allowed_variations)
    allowed_imperfections: List[AllowedImperfectionItem] = list(dna.allowed_imperfections)
    forbidden = list(dna.forbidden)

    restrictions = merge_restrictions(forbidden, prompt_rules)

    return ContentPromptContract(
        contract_version=contract_version,
        project=dna.project,
        prompt_type="content",
        prompt_id=f"{dna.subject}__content__{brief_slug}",
        prompt_version=prompt_version,
        generated_at=generated_at,
        source_knowledge=[dna.source_entry()],
        template=TemplateInfo(
            name=f"{template.prompt_type}_prompt.yaml", template_version=template.template_version
        ),
        task_brief=task_brief,
        target_language=target_language,
        required_dna=required_dna,
        allowed_variations=allowed_variations,
        allowed_imperfections=allowed_imperfections,
        forbidden=forbidden,
        final_prompt=render_final_prompt(task_brief, target_language, prompt_rules, required_dna, allowed_variations),
        restrictions=restrictions,
        optimizer=OptimizerInfo(used=False),
        validation=ValidationBlock(),
        notes=[],
    )
