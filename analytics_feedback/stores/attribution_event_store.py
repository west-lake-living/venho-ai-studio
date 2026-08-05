from __future__ import annotations

from analytics_feedback.stores.json_store import JsonDirectoryStore


class AttributionEventStore(JsonDirectoryStore):
    """Persists real `attribute_conversion_event()` results (2026-08-06) --
    before this, `venho-analytics attribute` only printed its output once
    and discarded it, so nothing downstream (Phase 7's strategy_memory
    pilot evidence collection) could ever read real attributed events back."""

    folder_name = "attribution_events"
