from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from prompt_studio.schemas.content_prompt import ContentPromptContract

from content_studio.schemas.content_output import ContentOutput, GeneratorInfo, SourcePromptRef, ValidationInfo
from content_studio.schemas.content_request import ContentRequest, SourceKnowledgeRef

GeneratedDraft = Dict[str, Any]
GeneratorFn = Callable[[ContentRequest, ContentPromptContract, Dict[str, Any]], GeneratedDraft]


class ForbiddenContentError(Exception):
    """Generated content contains a deterministic forbidden phrase before save."""


def _source_refs(request: ContentRequest, prompt: ContentPromptContract) -> List[SourceKnowledgeRef]:
    return [
        SourceKnowledgeRef(file=item.file, dna_version=item.dna_version, hash=item.hash)
        for item in prompt.source_knowledge
    ]


def _hashtags(platform: str, config: Dict[str, Any]) -> List[str]:
    rules = config.get("platform_rules", {}).get(platform, {})
    tags = rules.get("hashtags", ["#venhohotelhanoi", "#hotay", "#hanoi"])
    return list(tags[: rules.get("max_hashtags", 5)])


def _fact_map(prompt: ContentPromptContract) -> Dict[str, str]:
    return {item.key: item.value for item in prompt.required_dna}


def _natural_fact_sentence(prompt: ContentPromptContract, target_language: str) -> str:
    facts = _fact_map(prompt)
    water = facts.get("water_color")
    surface = facts.get("water_surface_texture")
    light = facts.get("light_quality")
    trees = facts.get("tree_density")
    if target_language == "en":
        parts = []
        if water:
            parts.append(f"West Lake carries a {water} tone")
        if surface or light:
            parts.append(f"the surface feels {surface or 'calm'} under {light or 'soft'} light")
        if trees:
            parts.append(f"trees remain {trees} around the view")
        return "; ".join(parts) if parts else "West Lake stays calm and local"
    parts = []
    if water:
        parts.append(f"Mặt nước Hồ Tây có sắc {water}")
    if surface or light:
        parts.append(f"mặt hồ {surface or 'calm'} dưới ánh sáng {light or 'soft'}")
    if trees:
        parts.append(f"mật độ cây quanh hồ ở mức {trees}")
    return "; ".join(parts) if parts else "Hồ Tây giữ nhịp sống bình tĩnh và gần gũi"


def mock_social_generator(
    request: ContentRequest,
    prompt: ContentPromptContract,
    config: Dict[str, Any],
) -> GeneratedDraft:
    fact_sentence = _natural_fact_sentence(prompt, request.target_language)
    if request.target_language == "en":
        hook = "A calm morning by West Lake"
        body = (
            f"{fact_sentence}. Ven Ho keeps the stay simple, clear, and close to the lake rhythm. "
            "Save this for an easy Hanoi stay when you want the day to begin gently."
        )
        cta = "Message Ven Ho to check room availability."
        title = "Morning at West Lake"
    elif request.target_language == "bilingual":
        hook = "Một buổi sáng bên Hồ Tây / A calm morning by West Lake"
        body = (
            f"{fact_sentence}. Ven Ho giữ cảm giác lưu trú gọn gàng, ấm áp, gần nhịp sống Hồ Tây. "
            "A simple base for an unhurried Hanoi morning."
        )
        cta = "Nhắn Ven Ho để xem phòng / Message Ven Ho to check availability."
        title = "Morning at West Lake"
    else:
        hook = "Một buổi sáng chậm bên Hồ Tây"
        body = (
            f"{fact_sentence}. Ven Ho giữ cảm giác lưu trú gọn gàng, ấm áp và gần với nhịp sống Hồ Tây. "
            "Hợp cho một ngày Hà Nội bắt đầu nhẹ nhàng, không vội vã."
        )
        cta = "Nhắn Ven Ho để xem phòng phù hợp cho lịch của bạn."
        title = "Một buổi sáng bên Hồ Tây"
    return {
        "title": title,
        "hook": hook,
        "body": body,
        "cta": cta,
        "hashtags": _hashtags(request.platform, config),
        "visual_note": "Use an existing West Lake or lake-view-room asset; Content Studio does not create images.",
    }


def _phrases_from_restrictions(prompt: ContentPromptContract) -> List[str]:
    phrases: List[str] = []
    for rule in [*prompt.restrictions, *(item.rule for item in prompt.forbidden)]:
        lowered = rule.lower()
        quoted = re.findall(r"'([^']+)'|\"([^\"]+)\"", lowered)
        phrases.extend(a or b for a, b in quoted)
        if "5 star" in lowered or "5 sao" in lowered:
            phrases.extend(["5 star", "five star", "5 sao"])
        if "best in hanoi" in lowered:
            phrases.append("best in hanoi")
    return [phrase for phrase in phrases if phrase]


def prefilter_forbidden(text: str, prompt: ContentPromptContract) -> None:
    lowered = text.lower()
    matches = sorted({phrase for phrase in _phrases_from_restrictions(prompt) if phrase in lowered})
    if matches:
        raise ForbiddenContentError(f"Draft contains forbidden phrase(s): {', '.join(matches)}")


def build_social_draft(
    request: ContentRequest,
    prompt: ContentPromptContract,
    config: Dict[str, Any],
    *,
    source_prompt_file: Optional[str] = None,
    generator_fn: GeneratorFn = mock_social_generator,
    generated_at: Optional[str] = None,
) -> ContentOutput:
    draft = generator_fn(request, prompt, config)
    text = "\n".join(str(draft.get(key, "")) for key in ("title", "hook", "body", "cta"))
    prefilter_forbidden(text, prompt)

    return ContentOutput(
        project=request.project,
        content_type=request.content_type,
        target_language=request.target_language,
        generated_at=generated_at or datetime.now(timezone.utc).isoformat(),
        source_knowledge=_source_refs(request, prompt),
        source_prompt=SourcePromptRef(
            file=source_prompt_file,
            prompt_id=prompt.prompt_id,
            prompt_version=prompt.prompt_version,
        ),
        generator=GeneratorInfo(),
        title=str(draft["title"]),
        hook=str(draft["hook"]),
        body=str(draft["body"]),
        cta=str(draft["cta"]),
        hashtags=list(draft.get("hashtags", [])),
        visual_note=draft.get("visual_note"),
        validation=ValidationInfo(required=request.validation_required),
    )
