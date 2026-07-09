"""Image Prompt Builder (§16 Step 5) — deterministic. Turns one DNA + a task brief into a
valid ImagePromptContract. Code decides the structure; no AI is involved at this stage
(that's the optional Optimizer, §8) — running this twice on the same input yields the same
required_dna, negative_prompt and final_prompt every time."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from prompt_studio.knowledge_reader import KnowledgeDna
from prompt_studio.negative_prompt import render_negative_prompt
from prompt_studio.schemas.base import (
    AllowedImperfectionItem,
    AllowedVariationItem,
    OptimizerInfo,
    RequiredDnaItem,
    TemplateInfo,
    ValidationBlock,
)
from prompt_studio.schemas.image_prompt import ImagePromptContract
from prompt_studio.template_loader import PromptTemplate, load_template


def render_final_prompt(
    task_brief: str,
    required_dna: List[RequiredDnaItem],
    allowed_variations: List[AllowedVariationItem],
    allowed_imperfections: List[AllowedImperfectionItem],
) -> str:
    """Assemble final_prompt from Knowledge only (§2.2) — no invented detail."""
    lines = [task_brief.strip(), ""]

    if required_dna:
        lines.append("Required details (must appear exactly as described):")
        lines.extend(f"- {item.key}: {item.value}" for item in required_dna)
        lines.append("")

    if allowed_variations:
        lines.append("Flexible aspects (any one of the listed options is acceptable):")
        lines.extend(f"- {item.key}: {' / '.join(item.value_range)}" for item in allowed_variations)
        lines.append("")

    if allowed_imperfections:
        lines.append("Authenticity — small imperfections are acceptable and expected:")
        lines.extend(f"- {item.value}" for item in allowed_imperfections)
        lines.append("")

    return "\n".join(lines).strip()


def build_image_prompt(
    dna: KnowledgeDna,
    task_brief: str,
    brief_slug: str,
    template: Optional[PromptTemplate] = None,
    prompt_version: str = "1.0",
    contract_version: str = "1.0",
    generated_at: Optional[str] = None,
) -> ImagePromptContract:
    """Build a Prompt JSON for one DNA + brief (§7.1, §8 Builder stage). `brief_slug` is a
    short slug (e.g. "booking-style") so two briefs for the same subject don't collide (§14)."""
    template = template or load_template("image")
    generated_at = generated_at or datetime.now(timezone.utc).isoformat()

    required_dna = list(dna.required_dna)
    allowed_variations = list(dna.allowed_variations)
    allowed_imperfections = list(dna.allowed_imperfections)
    forbidden = list(dna.forbidden)

    return ImagePromptContract(
        contract_version=contract_version,
        project=dna.project,
        prompt_type="image",
        prompt_id=f"{dna.subject}__image__{brief_slug}",
        prompt_version=prompt_version,
        generated_at=generated_at,
        source_knowledge=[dna.source_entry()],
        template=TemplateInfo(
            name=f"{template.prompt_type}_prompt.yaml", template_version=template.template_version
        ),
        task_brief=task_brief,
        target_language="en",
        required_dna=required_dna,
        allowed_variations=allowed_variations,
        allowed_imperfections=allowed_imperfections,
        forbidden=forbidden,
        final_prompt=render_final_prompt(task_brief, required_dna, allowed_variations, allowed_imperfections),
        negative_prompt=render_negative_prompt(forbidden),
        optimizer=OptimizerInfo(used=False),
        validation=ValidationBlock(),
        notes=[],
    )
