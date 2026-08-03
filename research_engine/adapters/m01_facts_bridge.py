from __future__ import annotations

from pathlib import Path
from typing import Any

from knowledge_studio.facts.fact_store import FactStore


class M01FactsBridge:
    def __init__(self, project: str = "venho_hotel", data_root: Path = Path("data/projects")) -> None:
        self.store = FactStore(project=project, data_root=data_root)

    def save_approved_fact(self, fact: dict[str, Any]) -> Path:
        return self.store.save(fact)
