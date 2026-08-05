from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class EvergreenPoolStore:
    """JSON-file store for pre-approved evergreen posts (plan v3.1 §9.3
    "Evergreen Pool -- mạng an toàn", PB-004).

    Mirrors `TrendCandidateStore`'s shape/locking assumptions (single-writer
    CLI, no fcntl lock -- unlike `PublicationRegistry`, this is never written
    concurrently by a cron run and a dashboard click). Items are added by
    Harry explicitly promoting a publication that already went out once
    (`add_from_publication`) -- there is no code path that invents evergreen
    content; only a human curates what goes in the pool.
    """

    def __init__(self, project: str = "venho_hotel", data_root: Path = Path("data/projects")) -> None:
        self.path = data_root / project / "growth" / "evergreen_pool.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

    def _save(self, items: list[dict[str, Any]]) -> None:
        self.path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

    def add_from_publication(self, publication: dict[str, Any], *, added_by: str) -> dict[str, Any]:
        """Promote an already-dispatched/reconciled publication into the
        pool. `publication` is a row from `PublicationRegistry` -- the
        caller (CLI `evergreen-add`) is responsible for only pointing this
        at content Harry actually wants reused (no automatic promotion)."""
        item = {
            "id": f"evergreen-{uuid.uuid4().hex[:8]}",
            "source_publication_id": publication.get("publication_id"),
            "platform": publication.get("platform"),
            "dna_subject": publication.get("dna_subject"),
            "content": publication.get("content"),
            "status": "approved",
            "added_by": added_by,
            "added_at": datetime.now(timezone.utc).isoformat(),
            "last_used_at": None,
        }
        items = self.load()
        items.append(item)
        self._save(items)
        return item

    def list_items(self) -> list[dict[str, Any]]:
        return self.load()

    def mark_used(self, item_id: str, *, used_at: datetime | None = None) -> None:
        when = (used_at or datetime.now(timezone.utc)).isoformat()
        items = self.load()
        for item in items:
            if item["id"] == item_id:
                item["last_used_at"] = when
                self._save(items)
                return
        raise KeyError(f"Unknown evergreen item id: {item_id}")
