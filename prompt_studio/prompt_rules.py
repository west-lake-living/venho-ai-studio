"""Loads config/projects/<project>/prompt_rules.yaml (§3.2) — project-level tone, audience,
CTA, brand_dna and restrictions for the content/seo builders."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent


class PromptRulesLoadError(Exception):
    """config/projects/<project>/prompt_rules.yaml is missing or malformed."""


def load_prompt_rules(project: str, repo_root: Path = _REPO_ROOT) -> Dict[str, Any]:
    path = repo_root / "config" / "projects" / project / "prompt_rules.yaml"
    if not path.exists():
        raise PromptRulesLoadError(f"No prompt_rules.yaml for project '{project}': {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))
