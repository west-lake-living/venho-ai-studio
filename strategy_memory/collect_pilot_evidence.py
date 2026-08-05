# STATUS (2026-08-06): real aggregation, wired into CLI `venho-strategy
# weekly-brief`. Joins two real stores that only started existing/being
# populated this session (SnapshotStore's real pillar field, the new
# AttributionEventStore) -- correctly returns an empty/near-empty list
# until real pilot traffic + attributed inquiries accumulate. Growth Agent
# only went live 2026-08-03/04, so an empty result here right now is the
# honest state, not a bug.
from __future__ import annotations

from pathlib import Path
from typing import Any

from analytics_feedback.stores import AttributionEventStore, SnapshotStore
from publishing_gateway.publication_registry import PublicationRegistry


def collect_pilot_snapshots(
    *, project: str = "venho_hotel", data_root: Path = Path("data/projects")
) -> list[dict[str, Any]]:
    """One row per real M08-observed publication:
    `{publication_id, pillar, platform, qualified_booking_signals, eligible_reach}`.

    Deliberately one row per publication (not pre-aggregated by group) --
    `strategy_memory.pattern_inference.infer_strategy_pattern`'s
    `min_sample_size` check counts *rows in the list you pass it*, so
    callers must filter this list down to one (pillar, platform) scope and
    pass the resulting per-publication rows straight through, not a single
    pre-summed dict (that would always look like "1 sample").

    `qualified_booking_signals` counts direct/assisted attribution results
    only (an `unattributed` event proves nothing about a specific
    publication and is excluded, real data only, no estimation).
    `eligible_reach` is that publication's real M08 `reach` metric.
    """
    registry = PublicationRegistry(project, data_root=data_root)
    publications = registry.load()["publications"]
    publications_by_id = {item["publication_id"]: item for item in publications}
    publications_by_package = {
        item["content_package_id"]: item for item in publications if item.get("content_package_id")
    }

    qualified_by_publication: dict[str, int] = {}
    for event in AttributionEventStore(project, data_root).list_all():
        if event.get("attribution_status") not in ("direct", "assisted"):
            continue
        publication_id = event.get("publication_id")
        if publication_id in publications_by_id:
            qualified_by_publication[publication_id] = qualified_by_publication.get(publication_id, 0) + 1

    rows: list[dict[str, Any]] = []
    for snapshot in SnapshotStore(project, data_root).list_all():
        publication = publications_by_package.get(snapshot.get("package_id"))
        if publication is None:
            continue
        publication_id = publication["publication_id"]
        rows.append(
            {
                "publication_id": publication_id,
                "pillar": publication.get("pillar") or "unknown",
                "platform": publication.get("platform") or "unknown",
                "qualified_booking_signals": qualified_by_publication.get(publication_id, 0),
                "eligible_reach": int((snapshot.get("metrics") or {}).get("reach") or 0),
            }
        )
    return rows
