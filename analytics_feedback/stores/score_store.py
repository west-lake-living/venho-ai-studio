from __future__ import annotations

from analytics_feedback.stores.json_store import JsonDirectoryStore


class ScoreStore(JsonDirectoryStore):
    folder_name = "scores"
