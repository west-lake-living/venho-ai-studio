from __future__ import annotations

"""Trend Radar fast lane: an approved upcoming West Lake event replaces the
nearest curated draft before the event (Harry's call, 2026-10-21).

Why: Saturday's special lane only drew from approved trends once a week, on
Monday, for that week's Saturday -- so the 10/10 fireworks (announced 05/10)
could never have been posted before they happened. Here an approved
`fast_lane` candidate is drafted into the latest cadence slot on or before
the event's start (never today: Harry still has to approve the draft), and
the curated PENDING_APPROVAL rows it displaces are CANCELLED, not deleted.

Never touches an approved/held/published slot or a research/trend draft, and
never approves anything: the new rows are ordinary PENDING_APPROVAL drafts.
"""

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from growth_orchestrator.application.daily_cycle import (
    CADENCE_DAYS,
    _WEEKDAY_INDEX,
    _slot_id_for,
    run_daily_cycle,
)
from publishing_gateway.publication_registry import REPLACEABLE_SLOT_STATUSES, PublicationRegistry
from research_engine.trend_radar.trend_candidate_store import TrendCandidateStore
from shared.jobs.slot_store import SlotStore

FAST_LANE_PILLAR = "Trend Radar"
DEFAULT_FAST_LANE_PLATFORMS = ["facebook", "instagram"]
_DAY_BY_INDEX = {index: day for day, index in _WEEKDAY_INDEX.items() if day in CADENCE_DAYS}


def _as_date(value: Any) -> Optional[date]:
    try:
        return date.fromisoformat(str(value)) if value else None
    except ValueError:
        return None


def ready_candidates(store: TrendCandidateStore, *, today: date) -> list[dict[str, Any]]:
    """Approved fast-lane events not yet drafted and not yet over."""
    ready = []
    for candidate in store.load():
        end = _as_date(candidate.get("event_end") or candidate.get("event_start"))
        if (
            candidate.get("fast_lane") is True
            and candidate.get("verified_by_human") is True
            and candidate.get("status") == "needs_human_approval"
            and not candidate.get("used_at")
            and not candidate.get("fast_lane_publication_ids")
            and end is not None
            and end > today
        ):
            ready.append(candidate)
    return ready


def candidate_slot_dates(candidate: dict[str, Any], *, today: date) -> list[tuple[str, str]]:
    """(slot_date, day) cadence slots from tomorrow up to the event start --
    or up to its last day when it is already running -- latest first, so the
    post lands as close before the event as possible."""
    start = _as_date(candidate.get("event_start"))
    end = _as_date(candidate.get("event_end")) or start
    if start is None or end is None:
        return []
    last = start if start > today else end
    slots = []
    current = today + timedelta(days=1)
    while current <= last:
        day = _DAY_BY_INDEX.get(current.weekday())
        if day:
            slots.append((current.isoformat(), day))
        current += timedelta(days=1)
    return list(reversed(slots))


def _is_curated_draft(row: dict[str, Any]) -> bool:
    brief = row.get("creative_brief") or {}
    return (
        row.get("status") == "PENDING_APPROVAL"
        and row.get("pillar") != FAST_LANE_PILLAR
        and not brief.get("proof_points")
    )


def pick_slot(
    candidate: dict[str, Any], registry: PublicationRegistry, *, today: date
) -> Optional[tuple[str, str, list[dict[str, Any]]]]:
    """Latest slot before the event whose owning rows are all curated drafts
    (or that has none). Returns (slot_date, day, rows_to_cancel)."""
    rows = registry.load()["publications"]
    for slot_date, day in candidate_slot_dates(candidate, today=today):
        slot_id = _slot_id_for(day, slot_date)
        owning = [r for r in rows if r.get("slot_id") == slot_id and r.get("status") not in REPLACEABLE_SLOT_STATUSES]
        if all(_is_curated_draft(r) for r in owning):
            return slot_date, day, owning
    return None


def fast_lane_topic(candidate: dict[str, Any]) -> dict[str, Any]:
    name = candidate.get("event_name") or candidate.get("title", "")
    start, end = candidate.get("event_start"), candidate.get("event_end")
    when = start if not end or end == start else f"{start} đến {end}"
    venue = candidate.get("venue") or "Hồ Tây"
    sources = ", ".join(sorted({s.get("source_name", "") for s in candidate.get("sources", []) if s.get("source_name")})[:3])
    return {
        "pillar": FAST_LANE_PILLAR,
        "dna_subject": candidate.get("dna_subject", "westlake"),
        "topic": name,
        "special_lane_type": candidate.get("type", "cultural_event"),
        "verified_by_human": True,
        "trend_candidate_id": candidate["id"],
        "research_backed": True,
        "proof_points": [
            {
                "text": f"{name} diễn ra {when} tại {venue}" + (f" (theo {sources})" if sources else ""),
                "fact_key": candidate["id"],
            }
        ],
    }


def run_fast_lane(
    *,
    project: str = "venho_hotel",
    data_root: Path = Path("data/projects"),
    today: Optional[date] = None,
    registry: Optional[PublicationRegistry] = None,
    store: Optional[TrendCandidateStore] = None,
    generate: Optional[Callable[..., Any]] = None,
) -> list[dict[str, Any]]:
    """Draft every ready fast-lane event once. Returns one outcome per
    candidate: drafted (with publication ids), no_free_slot, or failed.

    `generate` defaults to run_daily_cycle with the real image QC provider,
    like replace-rejected; tests inject a fake."""
    today = today or date.today()
    registry = registry or PublicationRegistry(project, data_root=data_root)
    store = store or TrendCandidateStore(project, data_root=data_root)
    slot_store = SlotStore(db_path=data_root / project / "growth" / "growth.db")
    generate = generate or run_daily_cycle
    now = datetime.now(timezone.utc).isoformat()

    outcomes: list[dict[str, Any]] = []
    for candidate in ready_candidates(store, today=today):
        outcome: dict[str, Any] = {
            "candidate_id": candidate["id"],
            "event_name": candidate.get("event_name") or candidate.get("title"),
            "event_start": candidate.get("event_start"),
        }
        picked = pick_slot(candidate, registry, today=today)
        if picked is None:
            outcome["status"] = "no_free_slot"
            outcome["alert"] = candidate.get("fast_lane_status") != "no_free_slot"
            store.annotate(candidate["id"], fast_lane_status="no_free_slot", fast_lane_checked_at=now)
            outcomes.append(outcome)
            continue

        slot_date, day, displaced = picked
        platforms = sorted({r["platform"] for r in displaced}) or DEFAULT_FAST_LANE_PLATFORMS
        previous = {r["publication_id"]: r["status"] for r in displaced}
        reason = f"replaced by Trend Radar fast lane: {outcome['event_name']} ({candidate['id']})"
        for publication_id in previous:
            registry.update(publication_id, status="CANCELLED", cancelled_reason=reason)
        result = None
        try:
            result = generate(
                day,
                project=project,
                platforms=platforms,
                data_root=data_root,
                image_validation_provider="openai",
                slot_store=slot_store,
                slot_date=slot_date,
                topic_override=fast_lane_topic(candidate),
            )
            if result.errors or not result.publications:
                raise RuntimeError(f"fast-lane generation incomplete: {result.errors}")
        except Exception as exc:  # noqa: BLE001 - restore the curated drafts, report, move on
            # A half-drafted slot (facebook ok, instagram failed) would block
            # restoring the curated row for that platform: retire it first.
            for publication in (result.publications if result is not None else []):
                if publication.get("publication_id") not in previous:
                    registry.update(publication["publication_id"], status="CANCELLED", cancelled_reason="fast lane partial failure")
            for publication_id, status in previous.items():
                registry.update(publication_id, status=status, cancelled_reason=None)
            store.annotate(candidate["id"], fast_lane_status="failed", fast_lane_error=str(exc)[:500], fast_lane_checked_at=now)
            outcomes.append({**outcome, "status": "failed", "error": str(exc)[:500], "alert": True})
            continue

        new_ids = [p["publication_id"] for p in result.publications]
        for publication in result.publications:
            same_platform = [pid for pid, _ in previous.items() if registry.find(pid)["platform"] == publication.get("platform")]
            if same_platform:
                registry.update(publication["publication_id"], replaces_publication_id=same_platform[0])
                registry.update(same_platform[0], replacement_publication_id=publication["publication_id"])
        store.annotate(
            candidate["id"],
            fast_lane_status="drafted",
            fast_lane_publication_ids=new_ids,
            fast_lane_slot_id=_slot_id_for(day, slot_date),
            used_at=now,
        )
        outcomes.append(
            {
                **outcome,
                "status": "drafted",
                "slot_id": _slot_id_for(day, slot_date),
                "publication_ids": new_ids,
                "cancelled_publication_ids": list(previous),
                "alert": True,
            }
        )
    return outcomes
