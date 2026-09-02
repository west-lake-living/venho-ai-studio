"""Atomic, fail-closed production release state for restoration routing."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProductionReleaseState:
    active_production_version: str = "mock"
    active_production_route: str = "mock"
    feature_flag_state: str = "OFF"
    release_id: str | None = None
    promotion_authority: str | None = None
    promotion_timestamp: str | None = None
    rollback_target: str = "comfyui-local"
    previous_stable_route: str = "comfyui-local"

    @property
    def candidate_v3_active(self) -> bool:
        return (
            self.active_production_version == "candidate-v3"
            and self.active_production_route == "candidate-v3"
            and self.feature_flag_state == "ON"
            and self.promotion_authority == "HUMAN"
        )


def load_production_release_state(path: Path) -> ProductionReleaseState:
    """Missing/corrupt/unapproved state resolves to the safe mock route."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        state = ProductionReleaseState(**data)
    except (FileNotFoundError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return ProductionReleaseState()
    if state.active_production_route not in {"mock", "comfyui-local", "candidate-v3"}:
        return ProductionReleaseState()
    if state.feature_flag_state not in {"ON", "OFF"}:
        return ProductionReleaseState()
    if state.feature_flag_state == "ON" and not state.candidate_v3_active:
        return ProductionReleaseState()
    return state


def write_production_release_state(path: Path, state: ProductionReleaseState) -> None:
    """Persist a complete release record atomically for restart-safe routing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(asdict(state), sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
