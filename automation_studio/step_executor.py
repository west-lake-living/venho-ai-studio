from __future__ import annotations

from automation_studio.action_registry import get_action, validate_params
from automation_studio.types import StepResult
from automation_studio.workflow_loader import WorkflowStep


def execute_step(step: WorkflowStep, dry_run: bool = False) -> StepResult:
    spec = get_action(step.action_key)
    validate_params(spec, step.params)
    if dry_run:
        return StepResult(status="success", message="dry-run")
    return spec.handler(**step.params)

