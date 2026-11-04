from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    def now_ms(self) -> int: ...


@runtime_checkable
class IdGenerator(Protocol):
    def new_id(self) -> str: ...
