from __future__ import annotations

from pathlib import Path
from typing import Any

from automation_studio.paths import BASE_DIR, resolve_path
from automation_studio.types import StepResult


def vision_mode_a(input: str, output: str | None = None, project: str | None = None, settings: dict[str, Any] | None = None) -> StepResult:
    from knowledge_studio.vision.pipeline import run_mode_a

    settings = settings or {}
    provider = settings.get("provider") or ("mock" if settings.get("mock") else None)
    results = run_mode_a(
        input_dir=resolve_path(input),
        output_dir=resolve_path(output) if output else None,
        provider=provider,
    )
    outputs = [path for item in results for path in item.values()]
    return StepResult(status="success", outputs=outputs, data={"project": project, "count": len(results)})


def vision_mode_b(project: str, subject: str, input: str, settings: dict[str, Any] | None = None) -> StepResult:
    from knowledge_studio.vision.pipeline import run_mode_b

    settings = settings or {}
    provider = settings.get("provider") or ("mock" if settings.get("mock") else None)
    paths = run_mode_b(
        project=project,
        subject=subject,
        input_dir=resolve_path(input),
        dna_version=str(settings.get("dna_version", "1.0")),
        provider=provider,
    )
    return StepResult(status="success", outputs=list(paths.values()), data={"project": project, "subject": subject})


def update_manifest(project: str, subject: str, settings: dict[str, Any] | None = None) -> StepResult:
    manifest_path = BASE_DIR / "data" / "projects" / project / "knowledge" / f"dna_manifest_{subject}.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Knowledge manifest not found: {manifest_path}")
    return StepResult(status="success", outputs=[manifest_path], data={"project": project, "subject": subject})

