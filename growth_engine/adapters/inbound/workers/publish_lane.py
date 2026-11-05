from __future__ import annotations

import fcntl
import logging
import urllib.error
import urllib.request
from collections.abc import Mapping
from pathlib import Path
from typing import Callable

from .loop import PeriodicTask, WorkerLoop


LOCKED_EXIT_CODE = 75
LaneHandler = Callable[[], object]


def build_publish_tasks(handlers: Mapping[str, LaneHandler]) -> tuple[PeriodicTask, ...]:
    """Build scheduler, expiry, and optional outbox dispatch ticks."""
    required = {"enqueue_due", "expire_overdue"}
    missing = sorted(required - handlers.keys())
    if missing:
        raise ValueError(f"missing publish-lane handlers: {', '.join(missing)}")
    health: dict[str, bool] = {
        "enqueue_due": False,
        "expire_overdue": False,
        "dispatch_outbox": False,
        "database": False,
    }

    def monitored(name: str, handler: LaneHandler, *, healthy_result: Callable[[object], bool] | None = None) -> LaneHandler:
        def run() -> object:
            try:
                result = handler()
            except Exception:
                health[name] = False
                raise
            health[name] = healthy_result(result) if healthy_result is not None else True
            return result
        return run

    tasks = [
        PeriodicTask("enqueue-due", monitored("enqueue_due", handlers["enqueue_due"]), interval_s=30),
        PeriodicTask("expire-overdue", monitored("expire_overdue", handlers["expire_overdue"]), interval_s=60),
    ]
    if "dispatch_outbox" in handlers:
        tasks.append(PeriodicTask(
            "dispatch-outbox", monitored("dispatch_outbox", handlers["dispatch_outbox"]), interval_s=5
        ))
    if "notifications" in handlers:
        tasks.append(PeriodicTask(
            "notifications", monitored("notifications", handlers["notifications"]), interval_s=5
        ))
    if "apply_receipts" in handlers:
        tasks.append(PeriodicTask("apply-receipts", handlers["apply_receipts"], interval_s=5))
    if "receipt_timeouts" in handlers:
        tasks.append(PeriodicTask("receipt-timeouts", handlers["receipt_timeouts"], interval_s=60))
    if "heartbeat" in handlers:
        if "database_health" not in handlers:
            raise ValueError("heartbeat requires a database_health handler")
        def check_database() -> object:
            return handlers["database_health"]()

        tasks.append(PeriodicTask(
            "heartbeat-database-check",
            monitored("database", check_database, healthy_result=_database_is_healthy),
            interval_s=60,
        ))

        def ping_if_healthy() -> object:
            required = ("enqueue_due", "expire_overdue", "dispatch_outbox", "database")
            if not all(health[name] for name in required):
                return False
            if "backup_is_fresh" in handlers and not bool(handlers["backup_is_fresh"]()):
                return False
            return handlers["heartbeat"]()

        tasks.append(PeriodicTask("heartbeat", ping_if_healthy, interval_s=60))
    return tuple(tasks)


def _database_is_healthy(result: object) -> bool:
    if isinstance(result, tuple) and result:
        return result[0] is True
    return result is True


class UrllibHeartbeatSender:
    """HTTP GET sender; failures are sanitized by the application heartbeat use case."""

    def ping(self, url: str) -> None:
        request = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=5.0) as response:
                if not 200 <= response.status < 300:
                    raise RuntimeError("heartbeat endpoint rejected ping")
        except (urllib.error.URLError, OSError):
            raise RuntimeError("heartbeat endpoint unavailable") from None


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
