from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Protocol

import yaml

from research_engine.local_beat.differ import build_beat_items, diff_week
from research_engine.local_beat.entities import BeatEntity, BeatItem, SearchResult, WeekSnapshot
from research_engine.local_beat.timeline_store import TimelineStore
from research_engine.local_beat.vault_writer import write_entity_note


class SearchProvider(Protocol):
    def search(self, query: str) -> list[SearchResult]:
        ...


class JsonSearchProvider:
    """Offline provider for tests and operator-provided research exports."""

    def __init__(self, path: Path) -> None:
        payload = json.loads(path.read_text(encoding="utf-8"))
        records = payload if isinstance(payload, list) else payload.get("results", [])
        self.records = [SearchResult.from_dict(item) for item in records]

    def search(self, query: str) -> list[SearchResult]:
        needle = query.casefold()
        return [item for item in self.records if needle in f"{item.title} {item.snippet} {item.content}".casefold()]


def load_watchlist(path: Path | None = None) -> list[BeatEntity]:
    source = path or Path(__file__).with_name("watchlist.yaml")
    payload = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    entities = [BeatEntity.from_dict(item) for item in payload.get("entities", [])]
    if not 15 <= len(entities) <= 30:
        raise ValueError(f"Local Beat watchlist must contain 15-30 entities, got {len(entities)}")
    return entities


def scan_week(
    week: str,
    *,
    provider: SearchProvider,
    watchlist_path: Path | None = None,
    store: TimelineStore | None = None,
    vault_root: Path = Path("vault"),
    now: datetime | None = None,
    allowed_sources: set[str] | None = None,
) -> list[BeatItem]:
    """Scan one query set per entity and return only changed beat items."""
    store = store or TimelineStore()
    detected_at = (now or datetime.now(timezone.utc)).isoformat()
    previous = store.load_snapshot(week)
    previous_week = store.load_snapshot(_previous_week(week))
    entities = load_watchlist(watchlist_path)
    current: list[BeatItem] = []
    for entity in entities:
        # One query per entity is the cost boundary.  Operators can reorder
        # the configured variants to choose the canonical weekly query; this
        # module is not a second high-volume news crawler.
        query = entity.queries[0]
        results = [
            item for item in provider.search(query)
            if allowed_sources is None or item.source in allowed_sources or any(
                item.url.casefold().find(source.casefold()) >= 0 for source in allowed_sources
            )
        ]
        current.extend(build_beat_items(entity, results, detected_at=detected_at))
    # Re-scanning the same week must be idempotent: compare against the last
    # materialised snapshot for that week if one exists, otherwise last week.
    changed = diff_week(current, previous or previous_week)
    snapshot = WeekSnapshot(week=week, items=tuple(current))
    store.save_snapshot(snapshot)
    for entity in entities:
        write_entity_note(entity, store.timeline(entity.id), vault_root=vault_root)
    return changed


def _previous_week(week: str) -> str:
    if "-W" not in week:
        raise ValueError(f"Expected an ISO week like '2026-W37', got {week!r}")
    year, raw_week = week.split("-W", 1)
    number = int(raw_week)
    if number > 1:
        return f"{year}-W{number - 1:02d}"
    # ISO years have 52 or 53 weeks; the prior year's last week is whichever
    # its Dec 28 falls in.
    return "{}-W{:02d}".format(int(year) - 1, date(int(year) - 1, 12, 28).isocalendar().week)
