from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal


Decision = Literal["continue", "simplify", "pivot", "kill"]


@dataclass
class LivingLabRun:
    run_id: str
    output_used: bool
    approved_first_try: bool
    retry_count: int
    minutes_saved: float
    cost_usd: float
    decision: Decision
    recorded_at: str = ""


def record_run(run: LivingLabRun, root: Path = Path("data/projects/venho_hotel/living_lab")) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    if not run.recorded_at:
        run.recorded_at = datetime.utcnow().isoformat()
    path = root / f"{run.run_id}.json"
    path.write_text(json.dumps(asdict(run), indent=2), encoding="utf-8")
    return path


def load_runs(root: Path = Path("data/projects/venho_hotel/living_lab")) -> list[LivingLabRun]:
    if not root.exists():
        return []
    return [LivingLabRun(**json.loads(path.read_text(encoding="utf-8"))) for path in sorted(root.glob("*.json"))]


def summarize_runs(runs: list[LivingLabRun]) -> dict[str, float | int | str]:
    total = len(runs)
    if total == 0:
        return {
            "runs": 0,
            "outputs_used": 0,
            "first_try_approval_rate": 0.0,
            "total_retries": 0,
            "minutes_saved": 0.0,
            "cost_usd": 0.0,
            "latest_decision": "none",
        }
    return {
        "runs": total,
        "outputs_used": sum(1 for run in runs if run.output_used),
        "first_try_approval_rate": round(sum(1 for run in runs if run.approved_first_try) / total, 4),
        "total_retries": sum(run.retry_count for run in runs),
        "minutes_saved": round(sum(run.minutes_saved for run in runs), 2),
        "cost_usd": round(sum(run.cost_usd for run in runs), 4),
        "latest_decision": runs[-1].decision,
    }
