from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml

from content_studio.prompt_bridge import PromptBridgeResult, build_content_prompt_for_request
from content_studio.schemas.content_request import ContentRequest

DEFAULT_DATA_ROOT = Path("data/projects")
DEFAULT_CONFIG_ROOT = Path("config/projects")


class ContentConfigError(Exception):
    """Content config is missing or malformed."""


@dataclass
class ContentContext:
    request: ContentRequest
    config: Dict[str, Any]
    prompt: PromptBridgeResult


def _read_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ContentConfigError(f"{path} must contain a mapping")
    return data


def load_content_config(project: str, config_root: Path = DEFAULT_CONFIG_ROOT) -> Dict[str, Any]:
    base = config_root / project / "content"
    config = {
        "content_pillars": _read_yaml(base / "content_pillars.yaml"),
        "tone_of_voice": _read_yaml(base / "tone_of_voice.yaml"),
        "platform_rules": _read_yaml(base / "platform_rules.yaml"),
        "seo_keywords": _read_yaml(base / "seo_keywords.yaml"),
        "calendar_rules": _read_yaml(base / "calendar_rules.yaml"),
    }
    forbidden_locations = [
        base / "forbidden_claims.yaml",
        base / "cta_rules.yaml",
    ]
    present = [str(path) for path in forbidden_locations if path.exists()]
    if present:
        raise ContentConfigError(
            "Content config must not define forbidden_claims or CTA rules; keep them in the prompt layer: "
            + ", ".join(present)
        )
    return config


def load_content_context(
    request: ContentRequest,
    *,
    config_root: Path = DEFAULT_CONFIG_ROOT,
    data_root: Path = DEFAULT_DATA_ROOT,
) -> ContentContext:
    config = load_content_config(request.project, config_root=config_root)
    prompt = build_content_prompt_for_request(request, data_root=data_root)
    return ContentContext(request=request, config=config, prompt=prompt)

