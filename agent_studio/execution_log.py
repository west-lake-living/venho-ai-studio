from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


class ExecutionLog:
    def __init__(self) -> None:
        self.entries: list[str] = []

    def add(self, message: str) -> None:
        self.entries.append(message)

    def save(self, project: str, plan_id: str, data_root: Path = Path("data/projects")) -> Path:
        path = data_root / project / "agents" / "logs" / f"{plan_id}.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        path.write_text("\n".join(f"{timestamp} {entry}" for entry in self.entries), encoding="utf-8")
        return path
