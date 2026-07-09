from __future__ import annotations

from analytics_feedback.stores.json_store import JsonDirectoryStore


class RawMetricsStore(JsonDirectoryStore):
    folder_name = "raw_metrics"
