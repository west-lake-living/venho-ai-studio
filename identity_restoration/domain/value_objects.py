from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# GW-D11: registry has three adapters from day one. "comfyui-local" wraps the
# already-running ComfyUIIdentityRestorer (patch v2.1 §2.3) — it is NOT the
# same id as v2.0's original "comfyui-remote" placeholder; remote is added in
# GW-P3 without renaming this one, so config never needs a silent migration.
RestorerId = Literal["comfyui-local", "comfyui-remote", "nano-banana-edit", "mock"]

WorkflowId = str


@dataclass(frozen=True)
class RestorationParams:
    """Sampler parameters. Bounds mirror contracts/restoration_request.schema.json.

    denoise is the most sensitive parameter in the whole pipeline: too low and
    the old face does not change; too high and head angle/lighting drift from
    Stage A. The 0.75 ceiling is a deliberate guard rail, not an arbitrary
    number (v2.0 §5.1).
    """

    denoise: float
    steps: int
    cfg: float
    sampler: str
    scheduler: str

    def __post_init__(self) -> None:
        if not (0.05 <= self.denoise <= 0.75):
            raise ValueError("denoise must be within [0.05, 0.75]")
        if not (8 <= self.steps <= 60):
            raise ValueError("steps must be within [8, 60]")
        if not (1.0 <= self.cfg <= 12.0):
            raise ValueError("cfg must be within [1.0, 12.0]")


@dataclass(frozen=True)
class VramClass:
    """Coarse VRAM budget class used by health/capacity checks (GW-P1/P3)."""

    total_mb: int
    free_mb: int

    @property
    def is_low(self) -> bool:
        return self.free_mb < 4200
