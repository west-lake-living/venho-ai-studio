from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from knowledge_studio.facts.fact_store import FactStore


class FactResolver:
    def __init__(self, project: str = "venho_hotel", data_root: Path = Path("data/projects")) -> None:
        self.store = FactStore(project=project, data_root=data_root)

    def resolve(self, fact_key: str, at: datetime | None = None) -> dict[str, Any] | None:
        fact = self.store.get(fact_key)
        if not fact or fact.get("status") != "approved":
            return None
        valid_from = datetime.fromisoformat(fact["valid_from"])
        valid_to_raw = fact.get("valid_to")
        valid_to = datetime.fromisoformat(valid_to_raw) if valid_to_raw else None
        if at:
            moment = at
        elif valid_from.tzinfo:
            moment = datetime.now(valid_from.tzinfo)
        else:
            moment = datetime.now()
        if moment.tzinfo is None and valid_from.tzinfo is not None:
            moment = moment.replace(tzinfo=valid_from.tzinfo)
        if moment < valid_from or (valid_to and moment > valid_to):
            return None
        return fact
