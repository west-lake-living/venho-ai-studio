from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from automation_studio.adapters import knowledge_adapter, prompt_adapter, validator_adapter
from automation_studio.errors import ActionRegistryError
from automation_studio.types import StepResult


@dataclass(frozen=True)
class ActionSpec:
    key: str
    handler: Callable[..., StepResult]
    required: tuple[str, ...] = ()
    optional: tuple[str, ...] = ()
    path_params: tuple[str, ...] = ()
    description: str = ""

    @property
    def allowed(self) -> set[str]:
        return set(self.required) | set(self.optional)


def _manual_gate(message: str, instructions: list[str] | None = None, next_actions: list[str] | None = None, settings: dict[str, Any] | None = None) -> StepResult:
    return StepResult(
        status="manual_gate",
        data={"message": message, "instructions": instructions or [], "next_actions": next_actions or []},
        message=message,
    )


REGISTRY: dict[str, ActionSpec] = {
    "knowledge_studio.vision_mode_a": ActionSpec(
        key="knowledge_studio.vision_mode_a",
        handler=knowledge_adapter.vision_mode_a,
        required=("input",),
        optional=("output", "project", "settings"),
        path_params=("input", "output"),
        description="Mode A image observations",
    ),
    "knowledge_studio.vision_mode_b": ActionSpec(
        key="knowledge_studio.vision_mode_b",
        handler=knowledge_adapter.vision_mode_b,
        required=("project", "subject", "input"),
        optional=("settings",),
        path_params=("input",),
        description="Mode B subject DNA build",
    ),
    "knowledge_studio.update_manifest": ActionSpec(
        key="knowledge_studio.update_manifest",
        handler=knowledge_adapter.update_manifest,
        required=("project", "subject"),
        optional=("settings",),
        description="Check Module 01 manifest exists",
    ),
    "prompt_studio.generate_prompt": ActionSpec(
        key="prompt_studio.generate_prompt",
        handler=prompt_adapter.generate_prompt,
        required=("project", "subject_or_subjects", "prompt_type", "brief"),
        optional=("target_language", "settings"),
        description="Generate a production prompt from DNA",
    ),
    "validator_studio.validate_image": ActionSpec(
        key="validator_studio.validate_image",
        handler=validator_adapter.validate_image,
        required=("project", "subject", "image_path"),
        optional=("dna_path", "prompt_path", "settings"),
        path_params=("image_path", "dna_path", "prompt_path"),
        description="Validate generated image output",
    ),
    "validator_studio.validate_prompt": ActionSpec(
        key="validator_studio.validate_prompt",
        handler=validator_adapter.validate_prompt,
        required=("project", "subject", "prompt_json_path"),
        optional=("dna_path", "settings"),
        path_params=("prompt_json_path", "dna_path"),
        description="Validate generated prompt JSON",
    ),
    "automation.manual_gate": ActionSpec(
        key="automation.manual_gate",
        handler=_manual_gate,
        required=("message",),
        optional=("instructions", "next_actions", "settings"),
        description="Pause workflow for a human action",
    ),
}


def get_action(key: str) -> ActionSpec:
    try:
        return REGISTRY[key]
    except KeyError as exc:
        raise ActionRegistryError(f"Unknown action: {key}") from exc


def validate_params(spec: ActionSpec, params: dict[str, Any]) -> None:
    missing = [name for name in spec.required if name not in params or params[name] in (None, "")]
    if missing:
        raise ActionRegistryError(f"{spec.key} missing required param(s): {', '.join(missing)}")
    unknown = sorted(set(params) - spec.allowed)
    if unknown:
        raise ActionRegistryError(f"{spec.key} has unknown param(s): {', '.join(unknown)}")


def list_actions() -> list[ActionSpec]:
    return [REGISTRY[key] for key in sorted(REGISTRY)]

