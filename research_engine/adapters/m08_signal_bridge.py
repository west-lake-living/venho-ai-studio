from __future__ import annotations

from pathlib import Path


class M08SignalBridge:
    def __init__(self, root: Path = Path("research/questions")) -> None:
        self.root = root

    def add_research_question(self, slug: str, question: str) -> Path:
        if not question.strip():
            raise ValueError("Research question is required")
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{slug}.md"
        path.write_text(question.strip() + "\n", encoding="utf-8")
        return path
