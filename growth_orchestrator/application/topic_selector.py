"""Topic selection with memory: cooldown + least-recently-used.

Why (2026-08-13): the old rotation was a bare modulo cursor over
content_pillars.yaml's flat topic list (`flat[index % len(flat)]`,
persisted in rotation_state.json). With 5 near-synonymous topics and a
cursor already at 41, every topic had been posted ~8 times and nothing ever
consulted the publication history -- Harry's 4 weekly posts read as the
same post repeated. This module is the fix: it is the one place a lane's
candidate topics turn into a single picked topic, and it always checks
PublicationRegistry first.

Design (Harry's call, 2026-08-13): prefer any candidate whose exact topic
text has not been posted within `cooldown_days`; rotate deterministically
among those. If every candidate is still inside its cooldown window, fall
back to the single least-recently-used one -- a slot must never go unfilled
for lack of a "fresh enough" topic.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

from publishing_gateway.publication_registry import PublicationRegistry

DEFAULT_COOLDOWN_DAYS = 60


def _rotation_state_path(project: str, data_root: Path) -> Path:
    return data_root / project / "growth" / "rotation_state.json"


def _load_rotation_state(project: str, data_root: Path) -> dict[str, int]:
    path = _rotation_state_path(project, data_root)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def advance_rotation(project: str, data_root: Path, key: str) -> int:
    """Advance and persist a named rotation cursor; returns the pre-advance
    index. One cursor per rotation_key so lanes never share a cursor.

    Public (not `_`-prefixed) because daily_cycle._pick_scenario also uses
    this for its own independent scenario-pool cursor -- same rotation_state
    .json, a different key (`scenario:<day>`) than any topic lane."""
    path = _rotation_state_path(project, data_root)
    state = _load_rotation_state(project, data_root)
    index = state.get(key, 0)
    state[key] = index + 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return index


def _last_used_at(topic_text: str, publications: list[dict[str, Any]]) -> Optional[datetime]:
    """Most recent created_at among past publications carrying this exact
    topic text. None means this topic has never been posted."""
    latest: Optional[datetime] = None
    for pub in publications:
        if pub.get("topic") != topic_text:
            continue
        created = pub.get("created_at")
        if not created:
            continue
        try:
            timestamp = datetime.fromisoformat(created)
        except ValueError:
            continue
        if latest is None or timestamp > latest:
            latest = timestamp
    return latest


def _in_cooldown(last_used: Optional[datetime], today: date, cooldown_days: int) -> bool:
    if last_used is None:
        return False
    return (today - last_used.date()).days < cooldown_days


def select_from_candidates(
    candidates: list[dict[str, Any]],
    *,
    project: str,
    data_root: Path,
    rotation_key: str,
    cooldown_days: int = DEFAULT_COOLDOWN_DAYS,
    today: Optional[date] = None,
    publications: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Pick one candidate dict (each must have a "topic" key).

    With an empty PublicationRegistry (the common case in tests, and any
    lane's very first weeks in production) every candidate is fresh, so
    this reduces to the same deterministic `flat[index % len(flat)]`
    rotation the old code did -- the cooldown/LRU logic only changes
    behaviour once real posting history exists.
    """
    if not candidates:
        raise ValueError(f"No topic candidates supplied for rotation_key='{rotation_key}'")

    today = today or date.today()
    if publications is None:
        publications = PublicationRegistry(project, data_root=data_root).load().get("publications", [])

    last_used = [_last_used_at(candidate["topic"], publications) for candidate in candidates]
    fresh = [candidate for candidate, used in zip(candidates, last_used) if not _in_cooldown(used, today, cooldown_days)]

    if fresh:
        index = advance_rotation(project, data_root, rotation_key)
        picked = dict(fresh[index % len(fresh)])
    else:
        # Every candidate is still inside cooldown: pick the one used
        # longest ago rather than leave the slot empty. Every entry here
        # has a real timestamp (a None last_used would already be "fresh").
        oldest_index = min(range(len(candidates)), key=lambda i: last_used[i])
        picked = dict(candidates[oldest_index])
        advance_rotation(project, data_root, rotation_key)  # keep the cursor moving for determinism

    picked.setdefault("research_backed", False)
    return picked
