from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


class JsonDirectoryStore:
    folder_name: str

    def __init__(self, project: str, data_root: Path = Path("data/projects")) -> None:
        self.project = project
        self.path = data_root / project / "analytics" / self.folder_name
        self.path.mkdir(parents=True, exist_ok=True)

    def save(self, item_id: str, payload: Any, overwrite: bool = False) -> Path:
        path = self.path / f"{item_id}.json"
        if path.exists() and not overwrite:
            return path
        data = payload.model_dump(mode="json") if hasattr(payload, "model_dump") else payload
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def load(self, item_id: str) -> Optional[dict]:
        path = self.path / f"{item_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list_all(self) -> list[dict]:
        """All saved items in this store, unordered. Added 2026-08-06 for
        `strategy_memory.collect_pilot_evidence`'s real cross-record
        aggregation -- callers that only ever needed one record at a time
        (save/load by id) predate this and are unaffected."""
        items = []
        for path in sorted(self.path.glob("*.json")):
            items.append(json.loads(path.read_text(encoding="utf-8")))
        return items
