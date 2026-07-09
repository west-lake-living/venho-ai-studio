"""Loads prompt_studio/templates/*.yaml (§11). Builders never inline YAML parsing so all
four prompt types stay structurally in sync and share one validation error message."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import yaml

TEMPLATES_DIR = Path(__file__).parent / "templates"

REQUIRED_TEMPLATE_FIELDS = ("template_version", "prompt_type", "sections", "rules")
REQUIRED_RULE_FIELDS = ("language", "max_length")


class TemplateLoadError(Exception):
    """A template YAML file is missing a required field."""


@dataclass
class PromptTemplate:
    template_version: str
    prompt_type: str
    sections: List[str]
    rules: Dict[str, Any]


def load_template(prompt_type: str) -> PromptTemplate:
    path = TEMPLATES_DIR / f"{prompt_type}_prompt.yaml"
    if not path.exists():
        raise TemplateLoadError(f"No template for prompt_type '{prompt_type}': {path}")

    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    missing = [f for f in REQUIRED_TEMPLATE_FIELDS if f not in data]
    if missing:
        raise TemplateLoadError(f"{path.name}: missing required field(s): {missing}")

    missing_rules = [f for f in REQUIRED_RULE_FIELDS if f not in data["rules"]]
    if missing_rules:
        raise TemplateLoadError(f"{path.name}: rules missing required field(s): {missing_rules}")

    return PromptTemplate(
        template_version=str(data["template_version"]),
        prompt_type=data["prompt_type"],
        sections=list(data["sections"]),
        rules=dict(data["rules"]),
    )
