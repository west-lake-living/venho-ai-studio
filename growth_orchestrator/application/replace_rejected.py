from __future__ import annotations

from datetime import date
from pathlib import Path
import re
from typing import Optional

from growth_orchestrator.application.daily_cycle import run_daily_cycle
from publishing_gateway.publication_registry import PublicationRegistry
from shared.jobs.slot_store import SlotStore

_SLOT_PATTERN = re.compile(r"^slot-(\d{4}-\d{2}-\d{2})-([a-z]+)$")


class ReplacementBatchError(RuntimeError):
    """Some replacements failed after the remaining candidates were tried."""

    def __init__(self, publications: list[dict], failures: list[dict[str, str]]) -> None:
        self.publications = publications
        self.failures = failures
        super().__init__(
            f"Replacement batch incomplete: {len(publications)} succeeded, "
            f"{len(failures)} failed: {failures}"
        )


def replace_rejected_publication(
    publication_id: str,
    *,
    project: str = "venho_hotel",
    data_root: Path = Path("data/projects"),
    registry: Optional[PublicationRegistry] = None,
) -> dict:
    """Generate a fresh, separately-reviewable draft for one rejected row."""
    registry = registry or PublicationRegistry(project, data_root=data_root)
    rejected = registry.find(publication_id)
    if rejected is None:
        raise KeyError(f"Unknown publication_id: {publication_id}")
    if rejected.get("status") != "REJECTED":
        raise ValueError(f"Publication {publication_id} is not REJECTED")
    if rejected.get("replacement_publication_id"):
        replacement = registry.find(rejected["replacement_publication_id"])
        return replacement or rejected

    match = _SLOT_PATTERN.match(rejected.get("slot_id") or "")
    if match is None:
        raise ValueError(f"Publication {publication_id} has no replaceable cadence slot")
    slot_date, day = match.groups()
    if date.fromisoformat(slot_date) < date.today():
        raise ValueError(f"Publication {publication_id} belongs to an expired slot")

    result = run_daily_cycle(
        day,
        project=project,
        platforms=[rejected["platform"]],
        data_root=data_root,
        image_validation_provider="openai",
        slot_store=SlotStore(db_path=data_root / project / "growth" / "growth.db"),
        slot_date=slot_date,
    )
    if result.errors or len(result.publications) != 1:
        raise RuntimeError(f"Replacement generation incomplete: {result.errors}")

    replacement_id = result.publications[0]["publication_id"]
    replacement = registry.update(replacement_id, replaces_publication_id=publication_id)
    registry.update(publication_id, replacement_publication_id=replacement_id)
    return replacement


def replace_due_rejections(
    *, project: str = "venho_hotel", data_root: Path = Path("data/projects"), limit: int = 8
) -> list[dict]:
    registry = PublicationRegistry(project, data_root=data_root)
    candidates = [
        row for row in registry.load()["publications"]
        if row.get("status") == "REJECTED"
        and not row.get("replacement_publication_id")
        and _SLOT_PATTERN.match(row.get("slot_id") or "")
        and date.fromisoformat(_SLOT_PATTERN.match(row["slot_id"]).group(1)) >= date.today()
    ][:limit]
    publications: list[dict] = []
    failures: list[dict[str, str]] = []
    for row in candidates:
        try:
            publications.append(
                replace_rejected_publication(
                    row["publication_id"], project=project, data_root=data_root, registry=registry
                )
            )
        except (KeyError, ValueError, RuntimeError) as exc:
            # One permanently bad row must not starve every later rejected
            # slot.  Keep processing and report the complete batch afterward.
            failures.append({"publication_id": row["publication_id"], "error": str(exc)})
    if failures:
        raise ReplacementBatchError(publications, failures)
    return publications
