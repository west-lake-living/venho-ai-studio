from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class VaultReader:
    def __init__(self, root: Path = Path("research")) -> None:
        self.root = root

    def read_frontmatter(self, path: Path) -> dict[str, Any]:
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            raise ValueError(f"Missing frontmatter: {path}")
        _, raw, _body = text.split("---", 2)
        loaded = yaml.safe_load(raw) or {}
        if not isinstance(loaded, dict):
            raise ValueError(f"Invalid frontmatter: {path}")
        return loaded

    def write_note(self, relative_path: Path, frontmatter: dict[str, Any], body: str) -> Path:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        fm = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=False).strip()
        path.write_text(f"---\n{fm}\n---\n\n{body.strip()}\n", encoding="utf-8")
        return path
