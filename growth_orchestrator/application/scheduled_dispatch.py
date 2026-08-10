from __future__ import annotations

"""Independent, pull-based dispatcher for approved Growth publications.

An external scheduler invokes this module frequently.  Approval never invokes
it: only rows already recorded as APPROVED_SCHEDULED and whose immutable
cadence slot is due can reach the publishing gateway.
"""

import os
from datetime import date, datetime, time, timedelta
from pathlib import Path
import re
from typing import Optional
from zoneinfo import ZoneInfo

from growth_orchestrator.application.approve_and_dispatch import (
    APPROVED_SCHEDULED_STATUS,
    DISPATCHING_STATUS,
    GATEWAY_ERROR_STATUS,
    _dispatch_claimed,
)
from growth_orchestrator.application.manage_slots import load_cadence_policy
from growth_orchestrator.bridges.m07_publishing_bridge import M07PublishingBridge, m07_publishing_bridge_from_env
from publishing_gateway.publication_registry import PublicationRegistry
from shared.jobs.slot_store import SlotStore

_SLOT_DATE_PATTERN = re.compile(r"^slot-(\d{4}-\d{2}-\d{2})-")
MAX_DISPATCH_LATENESS = timedelta(minutes=30)


def scheduled_at_for(publication: dict, *, cadence_policy: dict) -> datetime | None:
    """Resolve a publication's immutable slot to a timezone-aware datetime."""
    match = _SLOT_DATE_PATTERN.match(publication.get("slot_id") or "")
    if match is None:
        return None
    try:
        slot_date = date.fromisoformat(match.group(1))
        publish_time = time.fromisoformat(cadence_policy["publish_time"])
    except (KeyError, ValueError):
        return None
    return datetime.combine(slot_date, publish_time, tzinfo=ZoneInfo(cadence_policy["timezone"]))


def dispatch_due(
    *,
    project: str = "venho_hotel",
    data_root: Path = Path("data/projects"),
    config_root: Path = Path("config/projects"),
    registry: Optional[PublicationRegistry] = None,
    bridge: Optional[M07PublishingBridge] = None,
    slot_store: Optional[SlotStore] = None,
    now: Optional[datetime] = None,
    limit: int = 50,
    allow_shadow: bool = False,
    catch_up_today: bool = False,
) -> list[dict]:
    """Dispatch each due approved publication exactly once.

    The conditional registry claim is the concurrency boundary: overlapping
    scheduler ticks can see the same row, but only one can move it from
    APPROVED_SCHEDULED to DISPATCHING and therefore call Make.
    """
    cadence_policy = load_cadence_policy(project, config_root)
    timezone = ZoneInfo(cadence_policy["timezone"])
    current = now.astimezone(timezone) if now is not None else datetime.now(timezone)
    registry = registry or PublicationRegistry(project, data_root=data_root)
    bridge = bridge or m07_publishing_bridge_from_env(os.environ)
    slot_store = slot_store or SlotStore(db_path=data_root / project / "growth" / "growth.db")

    results: list[dict] = []
    for publication in registry.load()["publications"]:
        if len(results) >= limit or publication.get("status") != APPROVED_SCHEDULED_STATUS:
            continue
        scheduled_at = scheduled_at_for(publication, cadence_policy=cadence_policy)
        if scheduled_at is None or scheduled_at > current:
            continue
        # A manual recovery may release only today's missed slot.  It never
        # drains older backlog, so one catch-up cannot accidentally publish
        # several stale campaigns at once.
        is_today_catch_up = catch_up_today and scheduled_at.date() == current.date()
        if current - scheduled_at > MAX_DISPATCH_LATENESS and not is_today_catch_up:
            results.append(
                registry.update(
                    publication["publication_id"],
                    status=GATEWAY_ERROR_STATUS,
                    gateway_status="MISSED_DISPATCH_WINDOW",
                    gateway_error=(
                        f"Scheduled for {scheduled_at.isoformat()} but scheduler ran at "
                        f"{current.isoformat()} (maximum lateness: {MAX_DISPATCH_LATENESS})."
                    ),
                )
            )
            continue
        try:
            claimed = registry.claim(
                publication["publication_id"],
                expected_status=APPROVED_SCHEDULED_STATUS,
                claimed_status=DISPATCHING_STATUS,
            )
        except (KeyError, ValueError):
            # Another scheduler tick has already claimed the row.
            continue
        try:
            results.append(
                _dispatch_claimed(
                    claimed,
                    registry=registry,
                    bridge=bridge,
                    slot_store=slot_store,
                    project=project,
                    data_root=data_root,
                    allow_shadow=allow_shadow,
                )
            )
        except Exception as exc:  # never leave a claimed row stuck on a scheduler failure
            results.append(
                registry.update(
                    claimed["publication_id"],
                    status=GATEWAY_ERROR_STATUS,
                    gateway_status=GATEWAY_ERROR_STATUS,
                    gateway_error=str(exc),
                )
            )
    return results
