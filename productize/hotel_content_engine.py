from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def run_hotel_content_engine(*, project: str, brief: dict[str, Any], config_root: Path = Path("config/projects")) -> dict[str, Any]:
    project_root = config_root / project
    if not project_root.exists():
        raise ValueError(f"Unknown project: {project}")
    tone_path = project_root / "content" / "tone_of_voice.yaml"
    growth_path = project_root / "growth" / "taxonomy.yaml"
    tone = yaml.safe_load(tone_path.read_text(encoding="utf-8")) if tone_path.exists() else {}
    taxonomy = yaml.safe_load(growth_path.read_text(encoding="utf-8")) if growth_path.exists() else {}
    hotel_name = brief.get("hotel_name") or project.replace("_", " ").title()
    objective = brief.get("objective", "drive qualified demand")
    return {
        "project": project,
        "engine": "hotel-content-engine",
        "content_package": {
            "headline": f"{hotel_name}: {objective}",
            "body": brief.get("single_minded_message", objective),
            "cta": brief.get("cta", "Book direct"),
            "tone_keys": sorted(tone.keys()),
            "taxonomy_version": taxonomy.get("version"),
        },
        "core_modified": False,
    }
