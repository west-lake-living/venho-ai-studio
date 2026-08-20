from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class LedgerEntry:
    run_id: str
    attempt_id: str
    status: str
    payload: dict[str, Any] = field(default_factory=dict)


class RestorationLedgerPort(Protocol):
    def append(self, entry: LedgerEntry) -> None:
        """Append-only JSONL. Write on SUCCESS and on FAILURE alike.
        A lost failed attempt makes a benchmark lie (v1.0 §9 rule 3, kept)."""
        ...
