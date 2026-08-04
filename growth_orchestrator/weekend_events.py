"""
weekend_events.py — curated real-world Hanoi weekend events for the Saturday
special lane ("Cuoi tuan o Tay Ho").

Harry (or anyone with repo access) edits
config/projects/{project}/growth/weekend_events.json directly -- a flat list
of events, each with a [start_date, end_date] window (inclusive, YYYY-MM-DD)
and status "approved"/"pending_approval". Only "approved" events whose window
overlaps the upcoming Sat/Sun are ever handed to the content generator --
this is the only source of event facts the LLM prompt is allowed to cite
(see content_studio.generators.social_prompts.WEEKEND_EVENTS_SYSTEM_PROMPT).
No live event-feed integration exists; this is a manually curated list by
design, same trust model as growth_orchestrator's seed_facts.json.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List

DEFAULT_CONFIG_ROOT = Path("config/projects")


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _upcoming_weekend(today: date) -> tuple[date, date]:
    """Saturday/Sunday of the weekend that contains or follows `today`."""
    days_to_saturday = (5 - today.weekday()) % 7
    saturday = today + timedelta(days=days_to_saturday)
    return saturday, saturday + timedelta(days=1)


def load_verified_weekend_events(
    project: str,
    *,
    config_root: Path = DEFAULT_CONFIG_ROOT,
    today: date | None = None,
) -> List[Dict[str, Any]]:
    """Return approved events overlapping the upcoming Sat/Sun window.

    An event is included if status == "approved" and its [start_date,
    end_date] window overlaps [saturday, sunday]. Malformed/empty entries
    (no name or dates) are skipped rather than raised -- the seed file may
    contain a blank placeholder while Harry has nothing to add yet.
    """
    path = config_root / project / "growth" / "weekend_events.json"
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    today = today or date.today()
    saturday, sunday = _upcoming_weekend(today)

    approved: List[Dict[str, Any]] = []
    for entry in raw:
        if entry.get("status") != "approved":
            continue
        name = entry.get("name")
        start_raw = entry.get("start_date")
        if not name or not start_raw:
            continue
        start = _parse_date(start_raw)
        end = _parse_date(entry["end_date"]) if entry.get("end_date") else start
        if end < saturday or start > sunday:
            continue
        approved.append(
            {
                "name": name,
                "start_date": start_raw,
                "end_date": entry.get("end_date") or start_raw,
                "location": entry.get("location", ""),
                "description": entry.get("description", ""),
                "source_link": entry.get("source_link", ""),
            }
        )
    return approved
