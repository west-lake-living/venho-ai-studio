"""Loads config/settings_prompt.yaml (§9.3)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent
SETTINGS_PATH = _REPO_ROOT / "config" / "settings_prompt.yaml"


def load_settings(path: Path = SETTINGS_PATH) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def max_length_for(prompt_type: str, path: Path = SETTINGS_PATH) -> int:
    return int(load_settings(path)["max_length"][prompt_type])
