from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class WorkflowDescriptor:
    workflow_id: str
    filename: str
    sha256: str
    models: tuple[str, ...]
    min_vram_mb: int


class WorkflowRepositoryPort(Protocol):
    def load(self, workflow_id: str) -> tuple[dict, WorkflowDescriptor]:
        """Read a workflow JSON and verify its sha256 against the pin.
        Hash mismatch is a hard fail — a workflow changed silently (GW-D6)."""
        ...
