from __future__ import annotations

from pathlib import Path


REQUIRED_SECTIONS = ["Runbook", "Rollback", "Budget", "Ownership"]


def validate_runbook(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    missing = [section for section in REQUIRED_SECTIONS if section.lower() not in text.lower()]
    return {"path": str(path), "valid": not missing, "missing": missing}
