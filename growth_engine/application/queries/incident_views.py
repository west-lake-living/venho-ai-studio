from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class IncidentViewsQuery:
    state: str = "OPEN"
    cursor: str | None = None
    limit: int = 50


class IncidentViewReader(Protocol):
    def load_incident_views(self, query: IncidentViewsQuery) -> dict[str, object]: ...


class GetIncidentViews:
    def __init__(self, reader: IncidentViewReader) -> None:
        self._reader = reader

    def execute(self, query: IncidentViewsQuery) -> dict[str, object]:
        if query.limit < 1 or query.limit > 50:
            raise ValueError("limit must be between 1 and 50")
        return self._reader.load_incident_views(query)
