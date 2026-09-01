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


def _slot_platform_key(publication: dict) -> tuple[str, str] | None:
    slot_id = publication.get("slot_id")
    platform = publication.get("platform")
    if not slot_id or not platform:
        return None
    return (str(slot_id), str(platform))


def _reached_gateway(publication: dict) -> bool:
    """Whether this row has already handed its slot's post to Make.

    A GATEWAY_ERROR row normally *did* reach Make (Make answered, we just
    could not read a usable receipt out of the reply), so its slot is spent.
    The one exception is MISSED_DISPATCH_WINDOW, which this module writes
    itself before any gateway call happens.
    """
    status = publication.get("status")
    if status in ("PUBLISHED", DISPATCHING_STATUS):
        return True
    return status == GATEWAY_ERROR_STATUS and publication.get("gateway_status") != "MISSED_DISPATCH_WINDOW"


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


def _retire_duplicate_slot_rows(
    publications: list[dict],
    *,
    registry: PublicationRegistry,
    cadence_policy: dict,
    current: datetime,
    catch_up_today: bool,
) -> int:
    """Cancel every due row but one per (slot_id, platform), before dispatch.

    One cadence slot means one post per platform.  A historical weekly-cycle
    bug left pairs of rows sharing a slot, and the dispatch loop published
    BOTH -- two real posts seconds apart on the brand's own page (Instagram
    2026-08-15, Facebook 2026-08-17 and 2026-08-26).  ``claim`` cannot catch
    this: it serialises concurrent ticks against one row and never sees a
    sibling.

    This runs as a pre-pass rather than inline because the registry's
    slot/platform ownership guard rejects the *winner's* own status update
    while a sibling still sits in an owning status -- resolving duplicates
    first is what keeps the legitimate post dispatchable at all.

    Returns how many rows were retired, so the caller knows to re-read.
    """
    spent_slots = {
        key
        for publication in publications
        if (key := _slot_platform_key(publication)) is not None and _reached_gateway(publication)
    }
    designated: dict[tuple[str, str], str] = {}
    retired = 0
    for publication in publications:
        status = publication.get("status")
        is_candidate = status == APPROVED_SCHEDULED_STATUS or (
            catch_up_today
            and status == GATEWAY_ERROR_STATUS
            and publication.get("gateway_status") == "MISSED_DISPATCH_WINDOW"
        )
        key = _slot_platform_key(publication)
        if not is_candidate or key is None:
            continue
        # Only rows the scheduler would actually act on this tick: a future
        # slot must keep both rows untouched until its own dispatch decides.
        scheduled_at = scheduled_at_for(publication, cadence_policy=cadence_policy)
        if scheduled_at is None or scheduled_at > current:
            continue
        if key not in spent_slots and key not in designated:
            designated[key] = publication["publication_id"]
            continue
        winner = designated.get(key)
        registry.update(
            publication["publication_id"],
            status="CANCELLED",
            cancelled_reason=(
                f"duplicate row for {key[0]}/{key[1]}: that slot's post "
                + (f"is already handled by {winner}" if winner else "has already reached the publishing gateway")
            ),
        )
        retired += 1
    return retired


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

    publications = registry.load()["publications"]
    if _retire_duplicate_slot_rows(
        publications,
        registry=registry,
        cadence_policy=cadence_policy,
        current=current,
        catch_up_today=catch_up_today,
    ):
        publications = registry.load()["publications"]

    results: list[dict] = []
    for publication in publications:
        status = publication.get("status")
        is_missed_window_retry = (
            catch_up_today
            and status == GATEWAY_ERROR_STATUS
            and publication.get("gateway_status") == "MISSED_DISPATCH_WINDOW"
        )
        if len(results) >= limit or (
            status != APPROVED_SCHEDULED_STATUS and not is_missed_window_retry
        ):
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
                expected_status=(GATEWAY_ERROR_STATUS if is_missed_window_retry else APPROVED_SCHEDULED_STATUS),
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
