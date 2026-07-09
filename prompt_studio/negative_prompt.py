"""Renders DNA `forbidden` into a visual negative_prompt string (§5.5). Shared by the image
and video builders so forbidden rules are rendered identically across prompt types."""

from __future__ import annotations

from pathlib import Path
from typing import List

import yaml

from prompt_studio.schemas.base import ForbiddenItem

_RULES_PATH = Path(__file__).parent / "templates" / "negative_prompt.yaml"


def _load_rules() -> dict:
    data = yaml.safe_load(_RULES_PATH.read_text(encoding="utf-8"))
    return data["rules"]


def render_negative_prompt(forbidden: List[ForbiddenItem]) -> str:
    """Join forbidden.rule strings into one negative_prompt string, deduped, order preserved."""
    rules = _load_rules()
    rule_texts = [item.rule for item in forbidden]

    if rules.get("dedupe", True):
        seen = set()
        deduped = []
        for text in rule_texts:
            if text not in seen:
                seen.add(text)
                deduped.append(text)
        rule_texts = deduped

    return rules.get("join_with", ", ").join(rule_texts)
