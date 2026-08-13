"""Approved research facts -> Wednesday's local_discovery topic candidates.

Why (2026-08-13): the research pipeline (research_engine/) already collects
and Harry already approves real local facts -- cafes, pagodas, running
exhibitions -- into ProposedFactStore, but nothing downstream ever read
`status == "approved"` rows back into a post. Every Wed/Fri/Mon brief's
`proof_points` was hardcoded to `[]` in daily_cycle._build_creative_brief.

Deliberately reads ONLY `status == "approved"` (Harry's call, 2026-08-13):
`pending_approval` facts are unverified extractor output and must never reach
a post a guest will read. `rejected` facts are excluded by construction.

Best-effort like _weather_context_for_saturday: a broken/missing fact store
must never block the Wednesday pipeline, which ran on the curated topic list
alone before this existed.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

from shared.storage.proposed_fact_store import APPROVED, ProposedFactStore

# DD/MM/YYYY or "DD/MM/YYYY - DD/MM/YYYY" as written by the local_events
# extractor (see config/projects/venho_hotel/research/research_questions.yaml).
_DATE_RANGE = re.compile(r"(\d{2}/\d{2}/\d{4})(?:\s*-\s*(\d{2}/\d{2}/\d{4}))?")


def _event_still_running(value: str, on_date: date) -> bool:
    """True when an event's value string has no end date, or ends on/after
    `on_date`. An unparseable value is treated as still-running rather than
    silently dropped -- a malformed date must not swallow a real fact."""
    match = _DATE_RANGE.search(str(value))
    if not match:
        return True
    end_raw = match.group(2) or match.group(1)
    try:
        end = datetime.strptime(end_raw, "%d/%m/%Y").date()
    except ValueError:
        return True
    return end >= on_date


def approved_local_facts(
    project: str,
    data_root: Path,
    *,
    domains: list[str],
    slot_date: date,
    limit: int = 6,
) -> list[dict[str, Any]]:
    """Approved facts from `domains`, expired local_events filtered out.

    Each item: {"fact_key", "value", "domain", "text"} where `text` is a
    ready-to-quote Vietnamese-safe summary line built from the fact's own
    `rationale` (already Vietnamese prose from the extractor).
    """
    if not domains:
        return []
    try:
        facts = ProposedFactStore(project, data_root=data_root).list_items(status=APPROVED)
    except Exception:  # noqa: BLE001 - a broken fact store must never block Wednesday's pipeline
        return []

    picked: list[dict[str, Any]] = []
    for fact in facts:
        if fact.get("domain") not in domains:
            continue
        if fact.get("domain") == "local_events" and not _event_still_running(fact.get("value", ""), slot_date):
            continue
        picked.append(
            {
                "fact_key": fact.get("fact_key", fact.get("id", "")),
                "value": fact.get("value", ""),
                "domain": fact.get("domain", ""),
                "text": fact.get("rationale") or f"{fact.get('fact_key', '')}: {fact.get('value', '')}",
            }
        )
        if len(picked) >= limit:
            break
    return picked


def local_intel_topic_entries(
    project: str,
    data_root: Path,
    *,
    domains: list[str],
    pillar: str,
    slot_date: Optional[date] = None,
) -> list[dict[str, Any]]:
    """Shapes approved_local_facts() into the same topic-entry shape
    topic_selector expects from content_pillars.yaml -- one entry per fact,
    topic text taken straight from the fact so the brief's
    single_minded_message names the real place/event.

    No `dna_subject` here on purpose: the lane's scenario (picked
    independently, see daily_cycle._pick_scenario) decides the image
    subject, not the topic text.
    """
    facts = approved_local_facts(project, data_root, domains=domains, slot_date=slot_date or date.today())
    entries = []
    for fact in facts:
        entries.append(
            {
                "pillar": pillar,
                "topic": fact["text"],
                "research_backed": True,
                "proof_points": [{"text": fact["text"], "fact_key": fact["fact_key"]}],
            }
        )
    return entries
