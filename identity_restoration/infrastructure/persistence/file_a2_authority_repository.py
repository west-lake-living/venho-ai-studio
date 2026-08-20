from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ...domain.entities import A2Authority


@dataclass
class FileA2AuthorityRepository:
    path: str

    def load(self) -> A2Authority:
        return A2Authority.from_bytes(Path(self.path).read_bytes())
