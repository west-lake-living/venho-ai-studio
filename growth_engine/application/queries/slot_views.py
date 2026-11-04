from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SlotViewsQuery:
    from_date: str
    to_date: str
    channel_ids: tuple[str, ...] = ()


class SlotViewReader(Protocol):
    def load_slot_views(self, query: SlotViewsQuery) -> dict[str, object]: ...


class GetSlotViews:
    def __init__(self, reader: SlotViewReader) -> None:
        self._reader = reader

    def execute(self, query: SlotViewsQuery) -> dict[str, object]:
        if not query.from_date or not query.to_date or query.from_date > query.to_date:
            raise ValueError("a valid inclusive date range is required")
        return self._reader.load_slot_views(query)
