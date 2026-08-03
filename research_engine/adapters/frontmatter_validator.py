from __future__ import annotations

from datetime import date
from pathlib import Path

from research_engine.adapters.vault_reader import VaultReader
from research_engine.domain.research_note import ResearchNote


def _coerce_frontmatter(data: dict) -> dict:
    coerced = dict(data)
    for key in ("collected_at", "expires_at", "event_start", "event_end"):
        value = coerced.get(key)
        if isinstance(value, date):
            coerced[key] = value.isoformat()
    return coerced


def validate_frontmatter(path: Path) -> ResearchNote:
    data = _coerce_frontmatter(VaultReader(path.parents[1] if path.is_absolute() else Path("research")).read_frontmatter(path))
    return ResearchNote.model_validate(data)
