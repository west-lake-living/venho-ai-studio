from __future__ import annotations

from datetime import datetime
from typing import Protocol


class ClockPort(Protocol):
    def now(self) -> datetime: ...

    def monotonic(self) -> float: ...
    # Exists so timeout/TTL tests do not need a real sleep.
