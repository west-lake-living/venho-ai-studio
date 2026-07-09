from __future__ import annotations

from typing import Any

from automation_studio.paths import resolve_path
from automation_studio.types import StepResult


def validate_image(
    project: str,
    subject: str,
    image_path: str,
    dna_path: str | None = None,
    prompt_path: str | None = None,
    settings: dict[str, Any] | None = None,
) -> StepResult:
    from validator_studio.validation_pipeline import run_image_validation

    settings = settings or {}
    provider = settings.get("provider", "mock")
    paths = run_image_validation(project, subject, resolve_path(image_path), resolve_path(prompt_path) if prompt_path else None, provider=provider)
    return StepResult(status="success", outputs=list(paths.values()), data={"project": project, "subject": subject, "dna_path": dna_path})


def validate_prompt(
    project: str,
    subject: str,
    prompt_json_path: str,
    dna_path: str | None = None,
    settings: dict[str, Any] | None = None,
) -> StepResult:
    from validator_studio.validation_pipeline import run_prompt_validation

    paths = run_prompt_validation(project, subject, resolve_path(prompt_json_path))
    return StepResult(status="success", outputs=list(paths.values()), data={"project": project, "subject": subject, "dna_path": dna_path})

