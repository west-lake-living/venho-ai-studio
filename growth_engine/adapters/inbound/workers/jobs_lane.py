from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Callable

from .loop import PeriodicTask
from growth_engine.application.content.generate_package import (
    GeneratePackage,
    GeneratePackageCommand,
)
from growth_engine.application.content.run_lanes import LanePackage, LanePackageFactory
from growth_engine.domain.kernel.hashing import canonical_json_bytes


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
    if "replacement" in handlers:
        # The card does not define a replacement cadence; process superseded targets
        # every 15 minutes so review-time replacements do not wait for the next weekly run.
        tasks.append(PeriodicTask("replacement", handlers["replacement"], interval_s=15 * 60))
    if "reminders" in handlers:
        tasks.append(PeriodicTask("review-reminders", handlers["reminders"], interval_s=15 * 60))
    if "daily_digest" in handlers:
        tasks.append(PeriodicTask("daily-digest", handlers["daily_digest"], cron_ict="20:00"))
    if "metrics" in handlers:
        # Keep analytics on the slower jobs lane; an exception is isolated by WorkerLoop.
        tasks.append(PeriodicTask("metrics-collector", handlers["metrics"], interval_s=15 * 60))
    return tuple(tasks)


class JobsLane:
    """Run the content jobs scheduler; failures are isolated by WorkerLoop."""

    def __init__(self, loop) -> None:
        self._loop = loop

    def run_forever(self) -> int:
        self._loop.run_forever()
        return 0


class GeneratePackageLaneFactory(LanePackageFactory):
    """Adapt package generation to the per-slot package factory port used by RunLanes."""

    def __init__(self, use_case: GeneratePackage, lane_store, *, package_spec_hash: str) -> None:
        self._use_case = use_case
        self._lane_store = lane_store
        self._package_spec_hash = package_spec_hash

    def create(
        self,
        slot_id: str,
        lane: str,
        *,
        excluded_topic_keys: tuple[str, ...],
    ) -> LanePackage:
        request = self._lane_store.draft_request(
            slot_id,
            lane,
            now_ms=0,
            recent_topics=excluded_topic_keys,
        )
        lane_hash = hashlib.sha256(
            canonical_json_bytes({"config_hash": self._package_spec_hash, "lane": lane})
        ).hexdigest()
        result = self._use_case.execute(
            GeneratePackageCommand(
                request=request,
                package_spec_hash=lane_hash,
                generator_version="legacy-adapter-v1",
                lane=lane,
            )
        )
        return LanePackage(result.package.id, result.package.topic_key)
