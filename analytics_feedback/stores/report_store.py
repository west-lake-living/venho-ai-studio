from __future__ import annotations

from pathlib import Path


class ReportStore:
    def __init__(self, project: str, data_root: Path = Path("data/projects")) -> None:
        self.path = data_root / project / "analytics" / "reports"
        self.path.mkdir(parents=True, exist_ok=True)

    def save_markdown(self, report_id: str, markdown: str) -> Path:
        path = self.path / f"{report_id}.md"
        path.write_text(markdown, encoding="utf-8")
        return path
