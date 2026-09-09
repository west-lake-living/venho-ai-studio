from __future__ import annotations

import json
from pathlib import Path

from research_engine.local_beat.entities import BeatItem, WeekSnapshot


class TimelineStore:
    def __init__(self, root: Path = Path("data/local_beat")) -> None:
        self.root = root
        self.snapshot_root = root / "snapshots"
        self.timeline_root = root / "timelines"
        self.snapshot_root.mkdir(parents=True, exist_ok=True)
        self.timeline_root.mkdir(parents=True, exist_ok=True)

    def snapshot_path(self, week: str) -> Path:
        return self.snapshot_root / f"{week}.json"

    def load_snapshot(self, week: str) -> WeekSnapshot | None:
        path = self.snapshot_path(week)
        if not path.exists():
            return None
        return WeekSnapshot.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def save_snapshot(self, snapshot: WeekSnapshot) -> Path:
        path = self.snapshot_path(snapshot.week)
        path.write_text(json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for item in snapshot.items:
            self._append_timeline(item)
        return path

    def _append_timeline(self, item: BeatItem) -> None:
        path = self.timeline_root / f"{item.entity_id}.json"
        history = []
        if path.exists():
            try:
                history = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                history = []
        if not any(
            entry.get("id") == item.id
            and entry.get("title") == item.title
            and entry.get("snippet") == item.snippet
            and entry.get("content") == item.content
            and entry.get("status") == item.status.value
            for entry in history
        ):
            history.append(item.to_dict())
            path.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def timeline(self, entity_id: str) -> list[BeatItem]:
        path = self.timeline_root / f"{entity_id}.json"
        if not path.exists():
            return []
        return [BeatItem.from_dict(item) for item in json.loads(path.read_text(encoding="utf-8"))]
