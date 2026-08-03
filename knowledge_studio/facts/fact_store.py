from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from shared.security import ensure_safe_slug


class FactStore:
    def __init__(self, project: str = "venho_hotel", data_root: Path = Path("data/projects")) -> None:
        self.path = data_root / project / "growth" / "facts"
        self.path.mkdir(parents=True, exist_ok=True)

    def save(self, fact: dict[str, Any], *, overwrite: bool = False) -> Path:
        key = ensure_safe_slug(fact["fact_key"], field="fact_key").replace(".", "__")
        path = self.path / f"{key}.json"
        if path.exists() and not overwrite:
            old = json.loads(path.read_text(encoding="utf-8"))
            fact = {**fact, "version": int(old.get("version", 0)) + 1}
        path.write_text(json.dumps(fact, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def get(self, fact_key: str) -> dict[str, Any] | None:
        path = self.path / f"{ensure_safe_slug(fact_key, field='fact_key').replace('.', '__')}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list_all(self) -> list[dict[str, Any]]:
        return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(self.path.glob("*.json"))]

    def load_seed_facts(self, seed_file: Path) -> list[Path]:
        facts = json.loads(seed_file.read_text(encoding="utf-8"))
        return [self.save(fact, overwrite=True) for fact in facts]
