from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


class _JsonDirectoryStore:
    """Minimal save/load/list_all JSON-file store, same shape as
    `analytics_feedback.stores.json_store.JsonDirectoryStore` but rooted at
    `data/projects/{project}/strategy/{folder_name}` instead of
    `.../analytics/{folder_name}` -- not reusing that class directly since
    its "analytics" path segment is hardcoded."""

    folder_name: str

    def __init__(self, project: str, data_root: Path = Path("data/projects")) -> None:
        self.project = project
        self.path = data_root / project / "strategy" / self.folder_name
        self.path.mkdir(parents=True, exist_ok=True)

    def save(self, item_id: str, payload: dict[str, Any], overwrite: bool = True) -> Path:
        path = self.path / f"{item_id}.json"
        if path.exists() and not overwrite:
            return path
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def load(self, item_id: str) -> Optional[dict[str, Any]]:
        path = self.path / f"{item_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list_all(self) -> list[dict[str, Any]]:
        return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(self.path.glob("*.json"))]


class StrategyBriefStore(_JsonDirectoryStore):
    """Weekly strategy briefs (`build_weekly_strategy_brief` output) --
    always `advisory_only: True`, `status: "pending_approval"` until a human
    separately promotes an individual recommendation via
    `PromotedStrategyStore` (never auto-applied, plan §14 Phase 7)."""

    folder_name = "weekly_briefs"


class PromotedStrategyStore(_JsonDirectoryStore):
    """Strategy patterns a founder has explicitly approved
    (`pattern_inference.promote_strategy_memory`, requires `approved_by`).
    Separate from `StrategyBriefStore` so "what's in this week's advisory
    brief" and "what's actually been approved to date" are never
    conflated."""

    folder_name = "promoted"
