from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from automation_studio.paths import STATE_DIR


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class StepState:
    id: str
    status: str = "pending"
    started_at: str | None = None
    finished_at: str | None = None
    outputs: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    attempts: int = 0
    reason: str | None = None


@dataclass
class RunState:
    run_id: str
    workflow_id: str
    project: str | None
    status: str = "running"
    resumable_from: str | None = None
    started_at: str = field(default_factory=now_iso)
    finished_at: str | None = None
    steps: list[StepState] = field(default_factory=list)
    manual_gate: dict[str, Any] | None = None
    warnings: list[str] = field(default_factory=list)

    def step(self, step_id: str) -> StepState:
        for item in self.steps:
            if item.id == step_id:
                return item
        item = StepState(id=step_id)
        self.steps.append(item)
        return item

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def state_path(run_id: str, state_dir: Path = STATE_DIR) -> Path:
    return state_dir / f"{run_id}.json"


def save_state(state: RunState, state_dir: Path = STATE_DIR) -> Path:
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_path(state.run_id, state_dir)
    path.write_text(json.dumps(state.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_state(run_id: str, state_dir: Path = STATE_DIR) -> RunState:
    raw = json.loads(state_path(run_id, state_dir).read_text(encoding="utf-8"))
    raw["steps"] = [StepState(**step) for step in raw.get("steps", [])]
    return RunState(**raw)

