"""SEO Prompt Builder (§16 Step 12) — deterministic. Same shape as the content builder
(no visual negative_prompt, restrictions instead) plus keyword_intent (§5.4)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from prompt_studio.knowledge_reader import KnowledgeDna
from prompt_studio.prompt_rules import load_prompt_rules
from prompt_studio.restrictions import merge_restrictions
from prompt_studio.schemas.base import (
    AllowedVariationItem,
    OptimizerInfo,
    RequiredDnaItem,
    TargetLanguage,
    TemplateInfo,
    ValidationBlock,
)
from prompt_studio.schemas.seo_prompt import SeoPromptContract
from prompt_studio.template_loader import PromptTemplate, load_template

_LANGUAGE_LABEL = {
    "vi": "Vietnamese",
    "en": "English",
    "bilingual": "both Vietnamese and English",
}


def render_final_prompt(
    task_brief: str,
    keyword_intent: str,
    target_language: TargetLanguage,
    prompt_rules: Dict[str, Any],
    required_dna: List[RequiredDnaItem],
    allowed_variations: List[AllowedVariationItem],
) -> str:
    lines = [task_brief.strip(), "", f"Write the content in {_LANGUAGE_LABEL[target_language]}.", ""]

    lines.append(f"Keyword intent: {keyword_intent}")
    lines.append(f"Reader profile: {prompt_rules['audience']}")
    lines.append("")

    lines.append(
        "SEO structure: an H1 matching the keyword intent, a short intro paragraph, "
        "2-4 body sections with descriptive subheadings, a closing call-to-action, "
        "and a meta description under 160 characters."
    )
    lines.append("")

    if prompt_rules.get("internal_link_hints"):
        lines.append("Internal link hints:")
        lines.extend(f"- {hint}" for hint in prompt_rules["internal_link_hints"])
        lines.append("")

    if required_dna:
        lines.append("Location/entity facts (must appear, do not alter):")
        lines.extend(f"- {item.key}: {item.value}" for item in required_dna)
        lines.append("")

    if allowed_variations:
        lines.append("Flexible details (any one of the listed options is acceptable):")
        lines.extend(f"- {item.key}: {' / '.join(item.value_range)}" for item in allowed_variations)
        lines.append("")

    lines.append(f"Call-to-action: {prompt_rules['cta_rule']}")

    return "\n".join(lines).strip()


def build_seo_prompt(
    dna: KnowledgeDna,
    task_brief: str,
    brief_slug: str,
    keyword_intent: str,
    target_language: Optional[TargetLanguage] = None,
    prompt_rules: Optional[Dict[str, Any]] = None,
    template: Optional[PromptTemplate] = None,
    prompt_version: str = "1.0",
    contract_version: str = "1.0",
    generated_at: Optional[str] = None,
) -> SeoPromptContract:
    """Build a SEO Prompt JSON from one brand/location DNA + a brief + keyword intent (§5.4)."""
    template = template or load_template("seo")
    generated_at = generated_at or datetime.now(timezone.utc).isoformat()
    prompt_rules = prompt_rules or load_prompt_rules(dna.project)
    target_language = target_language or prompt_rules["default_target_language"]

    required_dna = list(dna.required_dna)
    allowed_variations = list(dna.allowed_variations)
    allowed_imperfections = list(dna.allowed_imperfections)
    forbidden = list(dna.forbidden)
    restrictions = merge_restrictions(forbidden, prompt_rules)

    return SeoPromptContract(
        contract_version=contract_version,
        project=dna.project,
        prompt_type="seo",
        prompt_id=f"{dna.subject}__seo__{brief_slug}",
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
        final_prompt=render_final_prompt(
            task_brief, keyword_intent, target_language, prompt_rules, required_dna, allowed_variations
        ),
        restrictions=restrictions,
        keyword_intent=keyword_intent,
        optimizer=OptimizerInfo(used=False),
        validation=ValidationBlock(),
        notes=[],
    )
