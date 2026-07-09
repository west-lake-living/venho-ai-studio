from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from automation_studio.errors import WorkflowConfigError
from automation_studio.paths import WORKFLOW_DIR

VALID_ON_ERROR = {"stop", "continue", "skip_dependents"}
VALID_TRIGGER_TYPES = {"manual", "schedule", "folder_watch"}


@dataclass
class WorkflowStep:
    id: str
    module: str
    action: str
    params: dict[str, Any] = field(default_factory=dict)
    needs: list[str] = field(default_factory=list)
    on_error: str = "stop"

    @property
    def action_key(self) -> str:
        return f"{self.module}.{self.action}"


@dataclass
class Workflow:
    workflow_id: str
    name: str
    version: str
    project: str | None
    trigger: dict[str, Any]
    steps: list[WorkflowStep]
    output: dict[str, Any]
    source_path: Path


def _expand_value(value: Any, variables: dict[str, Any]) -> Any:
    if isinstance(value, str):
        def repl(match: re.Match[str]) -> str:
            key = match.group(1)
            return str(variables.get(key, match.group(0)))

        return re.sub(r"\$\{([^}]+)\}", repl, value)
    if isinstance(value, list):
        return [_expand_value(item, variables) for item in value]
    if isinstance(value, dict):
        return {key: _expand_value(item, variables) for key, item in value.items()}
    return value


def list_workflow_files(workflow_dir: Path = WORKFLOW_DIR) -> list[Path]:
    if not workflow_dir.exists():
        return []
    return sorted(workflow_dir.glob("*.yaml"))


def load_workflow_file(path: Path, project_override: str | None = None) -> Workflow:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise WorkflowConfigError(f"Invalid YAML in {path}: {exc}") from exc

    required = ("workflow_id", "name", "version", "steps")
    missing = [field for field in required if field not in raw]
    if missing:
        raise WorkflowConfigError(f"{path} missing required field(s): {', '.join(missing)}")

    project = project_override or raw.get("project")
    variables = {"project": project} if project else {}
    raw = _expand_value(raw, variables)

    steps: list[WorkflowStep] = []
    seen: set[str] = set()
    for index, item in enumerate(raw.get("steps") or [], start=1):
        if not isinstance(item, dict):
            raise WorkflowConfigError(f"{path} step #{index} must be a mapping")
        for field_name in ("id", "module", "action"):
            if field_name not in item:
                raise WorkflowConfigError(f"{path} step #{index} missing '{field_name}'")
        step_id = str(item["id"])
        if step_id in seen:
            raise WorkflowConfigError(f"{path} duplicate step id: {step_id}")
        seen.add(step_id)
        on_error = item.get("on_error", "stop")
        if on_error not in VALID_ON_ERROR:
            raise WorkflowConfigError(f"{path} step '{step_id}' has invalid on_error: {on_error}")
        steps.append(
            WorkflowStep(
                id=step_id,
                module=str(item["module"]),
                action=str(item["action"]),
                params=dict(item.get("params") or {}),
                needs=list(item.get("needs") or []),
                on_error=on_error,
            )
        )

    _validate_needs(steps, path)
    trigger = dict(raw.get("trigger") or {"type": "manual"})
    trigger_type = trigger.get("type", "manual")
    if trigger_type not in VALID_TRIGGER_TYPES:
        raise WorkflowConfigError(f"{path} has invalid trigger type: {trigger_type}")

    return Workflow(
        workflow_id=str(raw["workflow_id"]),
        name=str(raw["name"]),
        version=str(raw["version"]),
        project=project,
        trigger=trigger,
        steps=steps,
        output=dict(raw.get("output") or {}),
        source_path=path,
    )


def _validate_needs(steps: list[WorkflowStep], path: Path) -> None:
    ids = {step.id for step in steps}
    for step in steps:
        unknown = [need for need in step.needs if need not in ids]
        if unknown:
            raise WorkflowConfigError(f"{path} step '{step.id}' needs unknown step(s): {', '.join(unknown)}")

    visiting: set[str] = set()
    visited: set[str] = set()
    by_id = {step.id: step for step in steps}

    def visit(step_id: str) -> None:
        if step_id in visited:
            return
        if step_id in visiting:
            raise WorkflowConfigError(f"{path} has circular dependency at step '{step_id}'")
        visiting.add(step_id)
        for need in by_id[step_id].needs:
            visit(need)
        visiting.remove(step_id)
        visited.add(step_id)

    for step in steps:
        visit(step.id)


def load_workflow(workflow_id: str, project_override: str | None = None) -> Workflow:
    for path in list_workflow_files():
        workflow = load_workflow_file(path, project_override=project_override)
        if workflow.workflow_id == workflow_id:
            return workflow
    raise WorkflowConfigError(f"Workflow not found: {workflow_id}")


def list_workflows() -> list[Workflow]:
    return [load_workflow_file(path) for path in list_workflow_files()]
