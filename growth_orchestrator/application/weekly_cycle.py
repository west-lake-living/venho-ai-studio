from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from agent_studio.growth.reference_asset_resolver import ReferenceAssetResolver
from agent_studio.growth.scenario_registry import ScenarioRegistry
from content_studio.content_context import DEFAULT_CONFIG_ROOT, DEFAULT_DATA_ROOT
from growth_orchestrator.application.daily_cycle import (
    CADENCE_DAYS,
    SPECIAL_CADENCE_DAY,
    DailyCycleResult,
    run_daily_cycle,
)
from growth_orchestrator.bridges.m03_validator_bridge import M03ValidatorBridge
from growth_orchestrator.bridges.m05_content_bridge import M05ContentBridge
from growth_orchestrator.domain.publishing_slot import PublishingSlot
from publishing_gateway.publication_registry import PublicationRegistry
from shared.jobs.job_store import JobStore
from shared.jobs.slot_store import SlotStore
from shared.storage.google_drive import google_drive_uploader_from_env

_WEEKDAY_INDEX = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}


def _next_occurrence(day_name: str, *, on_or_after: date) -> date:
    """The next calendar date for `day_name` on or after `on_or_after`.

    Used to give each cadence day a real date within "this week's" batch --
    daily_cycle itself only knows weekday *names* (see its module docstring),
    not calendar dates, so weekly_cycle (which knows "today") is what binds
    PublishingSlot rows to an actual slot_date.
    """
    target = _WEEKDAY_INDEX[day_name]
    delta = (target - on_or_after.weekday()) % 7
    return on_or_after + timedelta(days=delta)

# Cadence order matters for the rotation cursor (_next_rotation_index in
# daily_cycle.py): running Mon/Wed/Fri/Sat in this order within a single
# call advances each lane's rotation the same way four separate cron ticks
# across the week would have, so the topics picked here match what the old
# per-day cron would have produced -- this just does all four in one sitting
# instead of trickling in through the week, so Harry can review a whole
# week's batch in a single VENHO OS Dashboard session.
WEEKLY_CADENCE_ORDER = ["monday", "wednesday", "friday", "saturday"]


@dataclass
class WeeklyCycleResult:
    days: list[DailyCycleResult] = field(default_factory=list)
    # True when a JobStore idempotency guard found this ISO week already
    # SUCCEEDED (e.g. the GitHub Actions workflow was manually re-triggered
    # or retried) and skipped regenerating the whole week's drafts a second
    # time. `days` stays empty in that case -- nothing ran.
    skipped_already_run: bool = False

    @property
    def publications(self) -> list[dict[str, Any]]:
        return [pub for day in self.days for pub in day.publications]


def run_weekly_cycle(
    *,
    project: str = "venho_hotel",
    platforms: Optional[list[str]] = None,
    config_root: Path = DEFAULT_CONFIG_ROOT,
    data_root: Path = DEFAULT_DATA_ROOT,
    registry: Optional[PublicationRegistry] = None,
    scenario_registry: Optional[ScenarioRegistry] = None,
    image_provider: Optional[Any] = None,
    reference_resolver: Optional[ReferenceAssetResolver] = None,
    generate_image: bool = True,
    content_bridge: Optional[M05ContentBridge] = None,
    validator_bridge: Optional[M03ValidatorBridge] = None,
    image_validation_provider: str = "mock",
    drive_uploader: Optional[Any] = None,
    slot_store: Optional[SlotStore] = None,
    job_store: Optional[JobStore] = None,
    start_date: Optional[date] = None,
) -> WeeklyCycleResult:
    """Generate a full week's cadence (Mon/Wed/Fri/Sat) in one run.

    Same per-day pipeline as run_daily_cycle -- called once per cadence day
    so a whole week's drafts land PENDING_APPROVAL together, instead of one
    day's worth appearing per cron tick across the week. Callers share one
    registry/scenario_registry/content_bridge/drive_uploader across all four
    days so the rotation cursor and dashboard review list behave exactly as
    if this ran from four separate `daily-cycle` invocations, and Drive auth
    only happens once per run instead of once per day.

    Two pieces of plan v3.1 infra are wired in here (adapted for the
    ephemeral GitHub Actions cron model, not the plan's original always-on
    worker daemon -- see shared.jobs.slot_store.SlotStore's docstring):

    - `slot_store` (default: real SlotStore next to the registry's growth.db)
      gets one PublishingSlot per cadence day of `start_date`'s week ensured
      up front, then each run_daily_cycle call fills/misses its own slot.
    - `job_store` (default: real JobStore, same growth.db) makes the whole
      weekly run idempotent per ISO week: if this ISO week's job already
      SUCCEEDED (e.g. the workflow was manually re-triggered or GitHub
      retried it), this returns immediately with
      `skipped_already_run=True` and does not regenerate/re-spend budget on
      a second batch of drafts for the same week. A prior run that FAILED
      is eligible for retry (see JobStore.requeue_retryable_failures).
    """
    registry = registry or PublicationRegistry(project, data_root=data_root)
    scenario_registry = scenario_registry or ScenarioRegistry.from_file()
    content_bridge = content_bridge or M05ContentBridge(
        config_root=config_root, data_root=data_root, scenario_registry=scenario_registry
    )
    if generate_image:
        drive_uploader = drive_uploader or google_drive_uploader_from_env(os.environ)

    growth_db = data_root / project / "growth" / "growth.db"
    slot_store = slot_store or SlotStore(db_path=growth_db)
    job_store = job_store or JobStore(db_path=growth_db)

    today = start_date or date.today()
    iso_year, iso_week, _ = today.isocalendar()
    week_key = f"{project}-weekly-{iso_year}-W{iso_week:02d}"
    job_store.requeue_retryable_failures()
    job_store.enqueue(
        # scheduled_at must be "now" (not the business slot_date) -- JobStore
        # .claim() only picks up rows whose scheduled_at has already passed
        # against real wall-clock time, and this job needs to be claimable
        # immediately, not on the simulated cadence date.
        job_id=week_key, idempotency_key=week_key, job_type="weekly_cycle",
        version="1", scheduled_at=datetime.now().isoformat(), trace_id=week_key, payload={"project": project},
    )
    claimed = job_store.claim(owner="weekly-cycle")
    if claimed is None or claimed["id"] != week_key:
        # Either nothing was READY (this week already SUCCEEDED, or is
        # currently RUNNING under another lease) or a *different* job won
        # the single-row claim query race -- either way this week's batch
        # is not this call's job to run.
        return WeeklyCycleResult(days=[], skipped_already_run=True)

    day_dates = {day: _next_occurrence(day, on_or_after=today) for day in WEEKLY_CADENCE_ORDER}
    try:
        slot_store.ensure_slots(
            PublishingSlot(
                slot_id=f"slot-{day_dates[day].isoformat()}-{day}",
                slot_date=day_dates[day].isoformat(),
                slot_type="special" if day == SPECIAL_CADENCE_DAY else "regular",
                lane="special" if day == SPECIAL_CADENCE_DAY else "regular",
            )
            for day in WEEKLY_CADENCE_ORDER
        )
    except Exception:  # noqa: BLE001 - slot bookkeeping must never block the real content run
        pass

    results: list[DailyCycleResult] = []
    try:
        for day in WEEKLY_CADENCE_ORDER:
            assert day in CADENCE_DAYS
            try:
                results.append(
                    run_daily_cycle(
                        day,
                        project=project,
                        platforms=platforms,
                        config_root=config_root,
                        data_root=data_root,
                        registry=registry,
                        scenario_registry=scenario_registry,
                        image_provider=image_provider,
                        reference_resolver=reference_resolver,
                        generate_image=generate_image,
                        content_bridge=content_bridge,
                        validator_bridge=validator_bridge,
                        image_validation_provider=image_validation_provider,
                        drive_uploader=drive_uploader,
                        slot_store=slot_store,
                        slot_date=day_dates[day].isoformat(),
                    )
                )
            except Exception as exc:  # noqa: BLE001 - one day's uncaught failure (e.g. topic config error) must not drop the rest of the week's batch
                results.append(
                    DailyCycleResult(
                        day=day,
                        topic={},
                        publications=[],
                        errors=[{"platform": "*", "error": f"{type(exc).__name__}: {exc}"}],
                    )
                )
    except Exception as exc:  # noqa: BLE001 - truly unexpected failure outside the per-day guard above -- mark the week retryable rather than leaving it stuck RUNNING forever
        job_store.fail(week_key, f"{type(exc).__name__}: {exc}")
        raise
    job_store.complete(week_key)
    return WeeklyCycleResult(days=results)
