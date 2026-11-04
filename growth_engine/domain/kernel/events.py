from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class DomainEvent:
    name: str
    aggregate_id: str
    at_ms: int
    data: Mapping[str, object]
