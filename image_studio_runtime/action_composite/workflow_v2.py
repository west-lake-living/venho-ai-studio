"""Provider-neutral Action Composite v2.1 orchestration primitives.

The module deliberately contains no network or image-generation call. It makes
the expensive boundary explicit: scene candidates are selected once, then the
chosen canvas is passed to the localized identity pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Optional, Protocol, Sequence

from pydantic import BaseModel, Field


class SceneComposer(Protocol):
    def generate(self, request: Mapping[str, object], *, count: int) -> Sequence["SceneCandidate"]: ...


class SceneCandidate(BaseModel):
    candidate_id: str
    image_path: str
    scores: dict[str, float] = Field(default_factory=dict)
    metadata: dict[str, object] = Field(default_factory=dict)

    def selection_score(self) -> float:
        # Face is intentionally absent: identity is repaired after the scene is
        # frozen. These weights reflect the action-composite plan's priority.
        weights = {"pose": 0.24, "anatomy": 0.22, "outfit": 0.18,
                   "environment": 0.16, "composition": 0.12, "lighting": 0.05,
                   "hair_compatibility": 0.03}
        available = [(weight, self.scores[name]) for name, weight in weights.items()
                     if name in self.scores]
        if not available:
            return 0.0
        total_weight = sum(weight for weight, _ in available)
        return round(sum(weight * score for weight, score in available) / total_weight, 4)


class CandidateSelector:
    """Select the strongest scene/action canvas without face-score bias."""

    def select(self, candidates: Iterable[SceneCandidate]) -> SceneCandidate:
        ordered = sorted(candidates, key=lambda item: (-item.selection_score(), item.candidate_id))
        if not ordered:
            raise ValueError("Action Composite requires at least one scene candidate")
        return ordered[0]


class RegionalGate(BaseModel):
    """Fail-closed approval contract for the final composite."""

    identity: Optional[float] = Field(default=None, ge=0, le=100)
    eyes_brows: Optional[float] = Field(default=None, ge=0, le=100)
    geometry: Optional[float] = Field(default=None, ge=0, le=100)
    anatomy: Optional[float] = Field(default=None, ge=0, le=100)
    outfit: Optional[float] = Field(default=None, ge=0, le=100)
    environment: Optional[float] = Field(default=None, ge=0, le=100)
    global_composite: Optional[float] = Field(default=None, ge=0, le=100)
    pixel_preservation: bool = False
    thresholds: dict[str, float] = Field(default_factory=lambda: {
        "identity": 90.0, "eyes_brows": 90.0, "geometry": 92.0,
        "anatomy": 90.0, "outfit": 90.0, "environment": 90.0,
        "global_composite": 90.0,
    })

    def evaluate(self) -> tuple[bool, list[str]]:
        failures: list[str] = []
        for name, threshold in self.thresholds.items():
            value = getattr(self, name)
            if value is None:
                failures.append(f"{name}_unvalidated")
            elif value < threshold:
                failures.append(f"{name}_below_threshold")
        if not self.pixel_preservation:
            failures.append("pixel_preservation_failed")
        return not failures, failures


@dataclass
class WorkflowLedger:
    """Small immutable-friendly trace for scene freeze and local convergence."""

    events: list[dict[str, object]] = field(default_factory=list)

    def record(self, state: str, **values: object) -> None:
        self.events.append({"state": state, **values})

    def as_manifest(self) -> dict[str, object]:
        return {"version": "action_composite_v2.1", "events": list(self.events)}


def select_scene_candidate(candidates: Iterable[SceneCandidate], ledger: Optional[WorkflowLedger] = None) -> SceneCandidate:
    selected = CandidateSelector().select(candidates)
    if ledger is not None:
        ledger.record("SELECT_CANDIDATE", candidate_id=selected.candidate_id,
                      selection_score=selected.selection_score())
    return selected
