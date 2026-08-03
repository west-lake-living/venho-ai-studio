from __future__ import annotations

from pathlib import Path

from shared.security import ensure_safe_slug


class NotebookLMHandoff:
    def __init__(self, root: Path = Path("research")) -> None:
        self.root = root

    def create_inbox(self, topic_slug: str, question: str, sources: list[str]) -> Path:
        if not question.strip():
            raise ValueError("Research question is required")
        folder = self.root / "_notebooklm_inbox" / ensure_safe_slug(topic_slug, field="topic_slug")
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "question.md").write_text(question.strip() + "\n", encoding="utf-8")
        (folder / "sources.md").write_text("\n".join(f"- {item}" for item in sources) + "\n", encoding="utf-8")
        return folder

    def verify_export(self, path: Path) -> bool:
        text = path.read_text(encoding="utf-8")
        return text.startswith("---\n") and "evidence_level: R2" in text and "expires_at:" in text
