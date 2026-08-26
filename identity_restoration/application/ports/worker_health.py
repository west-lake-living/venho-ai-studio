from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class WorkerStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"


@dataclass(frozen=True)
class WorkerHealth:
    status: WorkerStatus
    gpu_name: str | None = None
    vram_total_mb: int | None = None
    vram_free_mb: int | None = None
    torch_vram_total_mb: int | None = None
    torch_vram_free_mb: int | None = None
    latency_ms: float | None = None


class WorkerHealthPort(Protocol):
    def probe(self) -> WorkerHealth:
        """Return HEALTHY | DEGRADED | OFFLINE.

        Result MUST be cached with a TTL by the implementation. If OFFLINE,
        the use case MUST NOT submit — the job fails visibly, never silently,
        never a fake completion (invariant carried from v1.0 §13)."""
        ...
