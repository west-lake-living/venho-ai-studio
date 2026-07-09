"""Video Prompt Builder (§16 Step 10) — deterministic, multi-DNA (§5.2).

A video typically merges a character DNA (e.g. linh_an — face/identity) with one or more
environment DNAs (e.g. lake_view_room). Character invariants always win identity; a
scene's environment invariants always win the scene. If the same key name appears in
both, neither value is dropped — the collision is only recorded in `notes` (§5.2) since
character_lock and environment_dna are rendered as separate, clearly-scoped sections.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Tuple

from prompt_studio.knowledge_reader import KnowledgeDna
from prompt_studio.negative_prompt import render_negative_prompt
from prompt_studio.schemas.base import (
    AllowedImperfectionItem,
    AllowedVariationItem,
    ForbiddenItem,
    OptimizerInfo,
    RequiredDnaItem,
    SourceKnowledgeEntry,
    TemplateInfo,
    ValidationBlock,
)
from prompt_studio.schemas.video_prompt import VideoPromptContract
from prompt_studio.template_loader import PromptTemplate, load_template


def _dedupe_by_key(items: List[RequiredDnaItem], notes: List[str], label: str) -> List[RequiredDnaItem]:
    seen: dict = {}
    for item in items:
        if item.key in seen and seen[item.key].value != item.value:
            notes.append(
                f"{label} key '{item.key}' conflict between DNA sources — kept first value "
                f"'{seen[item.key].value}', dropped '{item.value}'"
            )
            continue
        if item.key not in seen:
            seen[item.key] = item
    return list(seen.values())


def _dedupe_forbidden(items: List[ForbiddenItem]) -> List[ForbiddenItem]:
    seen = set()
    deduped = []
    for item in items:
        if item.rule not in seen:
            seen.add(item.rule)
            deduped.append(item)
    return deduped


def _merge_variations(items: List[AllowedVariationItem]) -> List[AllowedVariationItem]:
    seen: dict = {}
    for item in items:
        seen.setdefault(item.key, item)
    return list(seen.values())


def _merge_imperfections(items: List[AllowedImperfectionItem]) -> List[AllowedImperfectionItem]:
    seen = set()
    deduped = []
    for item in items:
        if item.value not in seen:
            seen.add(item.value)
            deduped.append(item)
    return deduped


def render_final_prompt(
    task_brief: str,
    character_lock: Optional[List[RequiredDnaItem]],
    environment_dna: List[RequiredDnaItem],
    allowed_variations: List[AllowedVariationItem],
    allowed_imperfections: List[AllowedImperfectionItem],
    consistency_rules: List[str],
) -> str:
    lines = [task_brief.strip(), ""]

    if character_lock:
        lines.append("Character lock (identity must stay exactly consistent):")
        lines.extend(f"- {item.key}: {item.value}" for item in character_lock)
        lines.append("")

    if environment_dna:
        lines.append("Environment (scene details, must appear exactly as described):")
        lines.extend(f"- {item.key}: {item.value}" for item in environment_dna)
        lines.append("")

    if allowed_variations:
        lines.append("Flexible aspects (any one of the listed options is acceptable):")
        lines.extend(f"- {item.key}: {' / '.join(item.value_range)}" for item in allowed_variations)
        lines.append("")

    if allowed_imperfections:
        lines.append("Authenticity — small imperfections are acceptable and expected:")
        lines.extend(f"- {item.value}" for item in allowed_imperfections)
        lines.append("")

    if consistency_rules:
        lines.append("Consistency rules:")
        lines.extend(f"- {rule}" for rule in consistency_rules)
        lines.append("")

    return "\n".join(lines).strip()


def build_video_prompt(
    environment_dnas: List[KnowledgeDna],
    task_brief: str,
    brief_slug: str,
    character_dna: Optional[KnowledgeDna] = None,
    template: Optional[PromptTemplate] = None,
    prompt_version: str = "1.0",
    contract_version: str = "1.0",
    generated_at: Optional[str] = None,
) -> VideoPromptContract:
    """Build a video Prompt JSON from one optional character DNA + 1+ environment DNAs (§5.2)."""
    if not environment_dnas:
        raise ValueError("build_video_prompt requires at least one environment DNA")

    template = template or load_template("video")
    generated_at = generated_at or datetime.now(timezone.utc).isoformat()
    notes: List[str] = []

    character_lock = list(character_dna.required_dna) if character_dna else None
    environment_dna = _dedupe_by_key(
        [item for dna in environment_dnas for item in dna.required_dna], notes, "environment_dna"
    )

    consistency_rules: List[str] = []
    if character_dna:
        consistency_rules.append("Character identity must match character_lock exactly across every scene.")
    if environment_dna:
        consistency_rules.append("Environment details must match environment_dna exactly across every scene.")

    if character_lock:
        character_keys = {item.key for item in character_lock}
        environment_keys = {item.key for item in environment_dna}
        for key in sorted(character_keys & environment_keys):
            notes.append(
                f"key '{key}' present in both character and environment DNA — using the "
                f"environment value for the scene; the character value stays locked in character_lock (§5.2)"
            )
            consistency_rules.append(
                f"For '{key}', use the environment value in scene description; character identity for '{key}' is locked separately."
            )

    all_dnas = ([character_dna] if character_dna else []) + list(environment_dnas)
    required_dna = (character_lock or []) + environment_dna
    allowed_variations = _merge_variations([item for dna in all_dnas for item in dna.allowed_variations])
    allowed_imperfections = _merge_imperfections([item for dna in all_dnas for item in dna.allowed_imperfections])
    forbidden = _dedupe_forbidden([item for dna in all_dnas for item in dna.forbidden])

    source_knowledge: List[SourceKnowledgeEntry] = [dna.source_entry() for dna in all_dnas]
    subject_combo = "+".join(dna.subject for dna in all_dnas)

    final_prompt = render_final_prompt(
        task_brief, character_lock, environment_dna, allowed_variations, allowed_imperfections, consistency_rules
    )
    negative_prompt = render_negative_prompt(forbidden)

    return VideoPromptContract(
        contract_version=contract_version,
        project=all_dnas[0].project,
        prompt_type="video",
        prompt_id=f"{subject_combo}__video__{brief_slug}",
        prompt_version=prompt_version,
        generated_at=generated_at,
        source_knowledge=source_knowledge,
        template=TemplateInfo(
            name=f"{template.prompt_type}_prompt.yaml", template_version=template.template_version
        ),
        task_brief=task_brief,
        target_language="en",
        required_dna=required_dna,
        allowed_variations=allowed_variations,
        allowed_imperfections=allowed_imperfections,
        forbidden=forbidden,
        final_prompt=final_prompt,
        negative_prompt=negative_prompt,
        character_lock=character_lock,
        environment_dna=environment_dna or None,
        consistency_rules=consistency_rules or None,
        optimizer=OptimizerInfo(used=False),
        validation=ValidationBlock(),
        notes=notes,
    )
