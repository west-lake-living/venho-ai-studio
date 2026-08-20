from __future__ import annotations

from typing import Protocol

from ...domain.entities import A2Authority


class A2AuthorityRepositoryPort(Protocol):
    path: str

    def load(self) -> A2Authority:
        """Read the pinned A2-FRONT authority image and its sha256."""
        ...
