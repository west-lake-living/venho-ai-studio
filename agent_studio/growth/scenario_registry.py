from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml


DEFAULT_REGISTRY_PATH = Path("config/projects/venho_hotel/growth/scenario_registry.yaml")


@dataclass(frozen=True)
class ScenarioProfile:
    scenario_key: str
    display_name: str
    dna_subject: Optional[str]
    dna_version: str
    environment_reference: Optional[str]
    reference_asset_ids: tuple[str, ...]
    reference_mode: str
    required_entities: tuple[str, ...]
    forbidden_entities: tuple[str, ...]
    linh_an_allowed_actions: tuple[str, ...]

    @property
    def requires_dna_validation(self) -> bool:
        return bool(self.dna_subject)

    def to_prompt_patch(self) -> dict[str, Any]:
        return {
            "scenario_key": self.scenario_key,
            "dna_subject": self.dna_subject,
            "dna_version": self.dna_version,
            "reference_asset_ids": list(self.reference_asset_ids),
            "reference_mode": self.reference_mode,
            "required_entities": list(self.required_entities),
            "forbidden_entities": list(self.forbidden_entities),
        }


class ScenarioRegistry:
    def __init__(self, scenarios: dict[str, ScenarioProfile], *, version: int = 1) -> None:
        self.scenarios = scenarios
        self.version = version

    @classmethod
    def from_file(cls, path: Path = DEFAULT_REGISTRY_PATH) -> "ScenarioRegistry":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        scenarios: dict[str, ScenarioProfile] = {}
        for key, raw in (payload.get("scenarios") or {}).items():
            scenarios[key] = ScenarioProfile(
                scenario_key=key,
                display_name=raw.get("display_name") or key,
                dna_subject=raw.get("dna_subject"),
                dna_version=str(raw.get("dna_version") or "2.7"),
                environment_reference=raw.get("environment_reference"),
                reference_asset_ids=tuple(raw.get("reference_asset_ids") or ()),
                reference_mode=raw.get("reference_mode") or "none",
                required_entities=tuple(raw.get("required_entities") or ()),
                forbidden_entities=tuple(raw.get("forbidden_entities") or ()),
                linh_an_allowed_actions=tuple(raw.get("linh_an_allowed_actions") or ()),
            )
        return cls(scenarios, version=int(payload.get("version") or 1))

    def resolve(self, scenario_key: str, *, required_entities: list[str] | None = None, forbidden_entities: list[str] | None = None) -> ScenarioProfile:
        if scenario_key not in self.scenarios:
            raise ValueError(f"Unknown scenario_key: {scenario_key}")
        profile = self.scenarios[scenario_key]
        requested_required = set(required_entities or [])
        requested_forbidden = set(forbidden_entities or [])
        required = set(profile.required_entities) | requested_required
        forbidden = set(profile.forbidden_entities) | requested_forbidden
        conflict = sorted(required & forbidden)
        if conflict:
            raise ValueError(f"Scenario entity conflict: {', '.join(conflict)}")
        return ScenarioProfile(
            scenario_key=profile.scenario_key,
            display_name=profile.display_name,
            dna_subject=profile.dna_subject,
            dna_version=profile.dna_version,
            environment_reference=profile.environment_reference,
            reference_asset_ids=profile.reference_asset_ids,
            reference_mode=profile.reference_mode,
            required_entities=tuple(sorted(required)),
            forbidden_entities=tuple(sorted(forbidden)),
            linh_an_allowed_actions=profile.linh_an_allowed_actions,
        )
