from __future__ import annotations

from collections.abc import Mapping
from typing import Callable

from .loop import PeriodicTask


JobHandler = Callable[[], object]


def build_jobs_tasks(handlers: Mapping[str, JobHandler]) -> tuple[PeriodicTask, ...]:
    """Build the currently specified recurring jobs-lane schedule in ICT."""
    required = {"ensure_slots", "weekly", "fast"}
    missing = sorted(required - handlers.keys())
    if missing:
        raise ValueError(f"missing jobs-lane handlers: {', '.join(missing)}")

    tasks = [
        PeriodicTask("ensure-slots", handlers["ensure_slots"], cron_ict="00:10"),
        PeriodicTask("weekly-2000", handlers["weekly"], cron_ict="SUN 20:00"),
        PeriodicTask("weekly-2200", handlers["weekly"], cron_ict="SUN 22:00"),
    ]
    tasks.extend(
        PeriodicTask(f"fast-{hour:02d}40", handlers["fast"], cron_ict=f"{hour:02d}:40")
        for hour in range(7, 23)
    )
    if "metrics" in handlers:
        # Keep analytics on the slower jobs lane; an exception is isolated by WorkerLoop.
        tasks.append(PeriodicTask("metrics-collector", handlers["metrics"], interval_s=15 * 60))
    return tuple(tasks)
