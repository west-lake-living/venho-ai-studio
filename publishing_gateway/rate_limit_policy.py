from __future__ import annotations

from pathlib import Path
from typing import Dict

import yaml


def load_rate_limits(project: str, config_root: Path = Path("config/projects")) -> Dict[str, int]:
    path = config_root / project / "publishing" / "rate_limits.yaml"
    # Fix #5: return empty limits (no throttling) when the file is absent instead of crashing.
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {platform: int(config.get("max_per_minute", 0)) for platform, config in data.get("platforms", {}).items()}


def platform_within_limit(platform: str, sent_counts: Dict[str, int], limits: Dict[str, int]) -> bool:
    limit = limits.get(platform, 0)
    if limit <= 0:
        return True
    return sent_counts.get(platform, 0) < limit
