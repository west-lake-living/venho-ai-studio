from __future__ import annotations

from datetime import date
from pathlib import Path
import re
from typing import Optional

from growth_orchestrator.application.daily_cycle import run_daily_cycle
from growth_orchestrator.application.manage_slots import ensure_slot_horizon, load_cadence_policy
from publishing_gateway.publication_registry import PublicationRegistry
from shared.jobs.slot_store import SlotStore

# Steady-state operation drafts content for the whole cadence horizon almost
# immediately (OPEN -> PENDING_APPROVAL), so a plain ensure_slot_horizon()
# call at the default horizon virtually never finds an OPEN slot -- every
# slot in range is already spoken for. Extend the search this many times
# (each by one more full horizon) before giving up, so a replacement can
# still land somewhere reasonably close instead of failing forever.
_MAX_HORIZON_EXTENSIONS = 8

_SLOT_PATTERN = re.compile(r"^slot-(\d{4}-\d{2}-\d{2})-([a-z]+)$")
REPLACEABLE_STATUSES = {"REJECTED", "STALE_APPROVAL"}


class ReplacementBatchError(RuntimeError):
    """Some replacements failed after the remaining candidates were tried."""

    def __init__(self, publications: list[dict], failures: list[dict[str, str]]) -> None:
        self.publications = publications
        self.failures = failures
        super().__init__(
            f"Replacement batch incomplete: {len(publications)} succeeded, "
            f"{len(failures)} failed: {failures}"
        )


def _replacement_slot(
    publication: dict,
    *,
    project: str,
    data_root: Path,
    slot_store: SlotStore,
    today: date,
) -> tuple[str, str]:
    """Keep a future rejection in place; move an expired approval forward.

    A stale approval's original publishing time has already passed, so it
    must never be regenerated into that historical slot.  It consumes the
    nearest still-OPEN cadence slot instead, preserving the normal calendar
    rather than creating an unscheduled catch-up post.
    """
    match = _SLOT_PATTERN.match(publication.get("slot_id") or "")
    if match is None:
        raise ValueError(f"Publication {publication['publication_id']} has no replaceable cadence slot")
    slot_date, day = match.groups()
    if date.fromisoformat(slot_date) >= today:
        return slot_date, day

    base_horizon = load_cadence_policy(project)["slot_creation_horizon_days"]
    horizon_days = base_horizon
    future_open_slots: list = []
    for _ in range(_MAX_HORIZON_EXTENSIONS):
        ensure_slot_horizon(
            project=project, data_root=data_root, slot_store=slot_store, start_date=today, horizon_days=horizon_days
        )
        future_open_slots = [
            slot for slot in slot_store.list_all(status="OPEN") if date.fromisoformat(slot.slot_date) >= today
        ]
        if future_open_slots:
            break
        horizon_days += base_horizon
    if not future_open_slots:
        raise ValueError(
            f"Publication {publication['publication_id']} has no future OPEN cadence slot "
            f"even after extending the horizon to {horizon_days} days"
        )
    target = future_open_slots[0]
    target_match = _SLOT_PATTERN.match(target.slot_id)
    if target_match is None:  # defensive: SlotStore rows must use cadence ids
        raise ValueError(f"Replacement slot {target.slot_id} is not a cadence slot")
    return target_match.group(1), target_match.group(2)


def replace_rejected_publication(
    publication_id: str,
    *,
    project: str = "venho_hotel",
    data_root: Path = Path("data/projects"),
    registry: Optional[PublicationRegistry] = None,
    today: Optional[date] = None,
) -> dict:
    """Generate a fresh review draft for a rejected or expired approval."""
    registry = registry or PublicationRegistry(project, data_root=data_root)
    rejected = registry.find(publication_id)
    if rejected is None:
        raise KeyError(f"Unknown publication_id: {publication_id}")
    if rejected.get("status") not in REPLACEABLE_STATUSES:
        raise ValueError(f"Publication {publication_id} is not rejected or stale")
    if rejected.get("replacement_publication_id"):
        replacement = registry.find(rejected["replacement_publication_id"])
        return replacement or rejected

    cutoff = today or date.today()
    slot_store = SlotStore(db_path=data_root / project / "growth" / "growth.db")
    slot_date, day = _replacement_slot(
        rejected, project=project, data_root=data_root, slot_store=slot_store, today=cutoff
    )

    result = run_daily_cycle(
        day,
        project=project,
        platforms=[rejected["platform"]],
        data_root=data_root,
        image_validation_provider="openai",
        slot_store=slot_store,
        slot_date=slot_date,
    )
    if result.errors or len(result.publications) != 1:
        raise RuntimeError(f"Replacement generation incomplete: {result.errors}")

    replacement_id = result.publications[0]["publication_id"]
    replacement = registry.update(replacement_id, replaces_publication_id=publication_id)
    registry.update(publication_id, replacement_publication_id=replacement_id)
    return replacement


def replace_due_rejections(
    *, project: str = "venho_hotel", data_root: Path = Path("data/projects"), limit: int = 8, today: Optional[date] = None,
) -> list[dict]:
    registry = PublicationRegistry(project, data_root=data_root)
    cutoff = today or date.today()
    rows = registry.load()["publications"]
    candidates = [
        row for row in rows
        if row.get("status") in REPLACEABLE_STATUSES
        and not row.get("replacement_publication_id")
        and _SLOT_PATTERN.match(row.get("slot_id") or "")
    ]
    # A historical weekly-cycle bug could leave two rejected rows for the
    # same platform in one cadence slot.  The slot needs one replacement, not
    # one replacement per stale row (which creates duplicate posts and burns
    # duplicate image/text API calls).  Preserve registry order while
    # coalescing by the actual publishing identity.
    groups: dict[tuple[str, str], list[dict]] = {}
    for row in candidates:
        groups.setdefault((row["slot_id"], row["platform"]), []).append(row)

    publications: list[dict] = []
    failures: list[dict[str, str]] = []
    for group in list(groups.values())[:limit]:
        row = group[0]
        try:
            replacement = replace_rejected_publication(
                row["publication_id"], project=project, data_root=data_root, registry=registry, today=cutoff
            )
            publications.append(replacement)
            for duplicate in group[1:]:
                registry.update(
                    duplicate["publication_id"],
                    replacement_publication_id=replacement["publication_id"],
                )
        except (KeyError, ValueError, RuntimeError) as exc:
            # One permanently bad row must not starve every later rejected
            # slot.  Keep processing and report the complete batch afterward.
            failures.append({
                "publication_id": row["publication_id"],
                "group_publication_ids": [item["publication_id"] for item in group],
                "error": str(exc),
            })
    if failures:
        raise ReplacementBatchError(publications, failures)
    return publications
