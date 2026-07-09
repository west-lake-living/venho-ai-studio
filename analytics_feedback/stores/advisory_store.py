from __future__ import annotations

from analytics_feedback.stores.json_store import JsonDirectoryStore


class AdvisoryStore(JsonDirectoryStore):
    folder_name = "advisories"
