"""Merges DNA `forbidden` + prompt_rules.yaml `restrictions` into one deduped list (§5.5),
shared by the content and seo builders since both use restrictions instead of a visual
negative_prompt."""

from __future__ import annotations

from typing import Any, Dict, List

from prompt_studio.schemas.base import ForbiddenItem


def merge_restrictions(forbidden: List[ForbiddenItem], prompt_rules: Dict[str, Any]) -> List[str]:
    restrictions: List[str] = []
    seen = set()
    for text in [item.rule for item in forbidden] + list(prompt_rules.get("restrictions", [])):
        if text not in seen:
            seen.add(text)
            restrictions.append(text)
    return restrictions
