from __future__ import annotations

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
WORKFLOW_DIR = BASE_DIR / "config" / "workflows"
RUN_ROOT = BASE_DIR / "data" / "automation_runs"
LOG_DIR = RUN_ROOT / "logs"
REPORT_DIR = RUN_ROOT / "reports"
STATE_DIR = RUN_ROOT / "state"
LOCK_DIR = RUN_ROOT / "locks"


def ensure_run_dirs() -> None:
    for path in (LOG_DIR, REPORT_DIR, STATE_DIR, LOCK_DIR):
        path.mkdir(parents=True, exist_ok=True)


def resolve_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else BASE_DIR / path

