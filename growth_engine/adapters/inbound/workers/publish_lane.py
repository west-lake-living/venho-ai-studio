from __future__ import annotations

import fcntl
import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Callable

from .loop import PeriodicTask, WorkerLoop


LOCKED_EXIT_CODE = 75
LaneHandler = Callable[[], object]


def build_publish_tasks(handlers: Mapping[str, LaneHandler]) -> tuple[PeriodicTask, ...]:
    """Build the scheduler and expiry ticks owned by the single publish lane."""
    required = {"enqueue_due", "expire_overdue"}
    missing = sorted(required - handlers.keys())
    if missing:
        raise ValueError(f"missing publish-lane handlers: {', '.join(missing)}")
    return (
        PeriodicTask("enqueue-due", handlers["enqueue_due"], interval_s=30),
        PeriodicTask("expire-overdue", handlers["expire_overdue"], interval_s=60),
    )


class PublishLane:
    """Hold the single-instance fcntl lock while the publish scheduler runs."""

    def __init__(
        self,
        loop: WorkerLoop,
        lock_path: str | Path,
        *,
        log_error: Callable[[str], object] | None = None,
    ) -> None:
        self._loop = loop
        self._lock_path = Path(lock_path)
        self._log_error = log_error or logging.getLogger(__name__).error

    def run_forever(self) -> int:
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock_path.open("a+") as lock_file:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                self._log_error(
                    f"publish lane already running; exiting with code {LOCKED_EXIT_CODE} "
                    f"(lock: {self._lock_path})"
                )
                return LOCKED_EXIT_CODE
            self._loop.run_forever()
        return 0
