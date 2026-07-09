from __future__ import annotations

import os
from pathlib import Path

from automation_studio.errors import WorkflowLockError
from automation_studio.paths import LOCK_DIR


class RunLock:
    def __init__(self, workflow_id: str, lock_dir: Path = LOCK_DIR) -> None:
        self.workflow_id = workflow_id
        self.lock_dir = lock_dir
        self.path = lock_dir / f"{workflow_id}.lock"

    def acquire(self, run_id: str) -> None:
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            owner = self.path.read_text(encoding="utf-8").strip() if self.path.exists() else "unknown"
            raise WorkflowLockError(f"Workflow '{self.workflow_id}' is already running ({owner})") from exc
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(run_id)

    def release(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass

