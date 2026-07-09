from __future__ import annotations

from datetime import datetime
from pathlib import Path

from automation_studio.action_registry import get_action, validate_params
from automation_studio.errors import WorkflowConfigError
from automation_studio.paths import ensure_run_dirs, resolve_path
from automation_studio.report_builder import write_report
from automation_studio.run_lock import RunLock
from automation_studio.run_state import RunState, now_iso, save_state
from automation_studio.step_executor import execute_step
from automation_studio.workflow_loader import Workflow, WorkflowStep


def make_run_id(workflow_id: str) -> str:
    stamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
    return f"run_{stamp}_{workflow_id}"


def dry_run_workflow(workflow: Workflow) -> list[str]:
    warnings: list[str] = []
    dependents = {step.id: [] for step in workflow.steps}
    for step in workflow.steps:
        for need in step.needs:
            dependents[need].append(step.id)

    for step in workflow.steps:
        spec = get_action(step.action_key)
        validate_params(spec, step.params)
        if step.on_error == "continue" and dependents[step.id]:
            raise WorkflowConfigError(
                f"Step '{step.id}' uses on_error: continue but has dependent step(s): {', '.join(dependents[step.id])}"
            )
        for name in spec.path_params:
            value = step.params.get(name)
            if not value:
                continue
            path = resolve_path(value)
            if name in {"input", "image_path", "dna_path", "prompt_path", "prompt_json_path"} and not path.exists():
                raise WorkflowConfigError(f"Path for '{step.id}.{name}' does not exist: {path}")
            parent = path if path.suffix == "" else path.parent
            try:
                parent.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise WorkflowConfigError(f"Cannot create parent path for '{step.id}.{name}': {parent}") from exc
    return warnings


def run_workflow(workflow: Workflow, *, dry_run: bool = False, resume_from: str | None = None, run_id: str | None = None) -> tuple[RunState, Path | None]:
    ensure_run_dirs()
    if dry_run:
        dry_run_workflow(workflow)
        state = RunState(
            run_id=run_id or make_run_id(workflow.workflow_id),
            workflow_id=workflow.workflow_id,
            project=workflow.project,
            status="success",
            finished_at=now_iso(),
        )
        for step in workflow.steps:
            step_state = state.step(step.id)
            step_state.status = "success"
            step_state.reason = "dry-run"
        return state, None

    state = RunState(
        run_id=run_id or make_run_id(workflow.workflow_id),
        workflow_id=workflow.workflow_id,
        project=workflow.project,
    )
    lock = RunLock(workflow.workflow_id)
    lock.acquire(state.run_id)
    report_path: Path | None = None
    try:
        _execute_steps(workflow, state, resume_from=resume_from)
        if state.status == "running":
            state.status = _final_status(state)
        state.finished_at = now_iso()
        save_state(state)
        report_path = write_report(state, workflow)
        return state, report_path
    finally:
        if state.finished_at is None:
            state.finished_at = now_iso()
            if state.status == "running":
                state.status = _final_status(state)
            save_state(state)
            report_path = write_report(state, workflow)
        lock.release()


def _execute_steps(workflow: Workflow, state: RunState, resume_from: str | None = None) -> None:
    status_by_id: dict[str, str] = {}
    skipping_until_resume = bool(resume_from)

    for step in workflow.steps:
        step_state = state.step(step.id)
        if skipping_until_resume and step.id != resume_from:
            step_state.status = "skipped"
            step_state.reason = f"resume skips completed step before {resume_from}"
            status_by_id[step.id] = "success"
            continue
        skipping_until_resume = False

        failed_needs = [need for need in step.needs if status_by_id.get(need) not in {"success"}]
        if failed_needs:
            step_state.status = "skipped"
            step_state.reason = f"dependency not successful: {', '.join(failed_needs)}"
            status_by_id[step.id] = step_state.status
            continue

        step_state.status = "running"
        step_state.started_at = now_iso()
        step_state.attempts += 1
        save_state(state)

        try:
            result = execute_step(step)
        except Exception as exc:  # noqa: BLE001 - automation records module failures uniformly
            step_state.status = "failed"
            step_state.reason = str(exc)
            step_state.finished_at = now_iso()
            state.resumable_from = step.id
            status_by_id[step.id] = step_state.status
            save_state(state)
            if step.on_error == "stop":
                state.status = "failed"
                return
            if step.on_error == "skip_dependents":
                _skip_dependents(workflow, state, step.id, reason=f"dependency failed: {step.id}")
            continue

        step_state.finished_at = now_iso()
        step_state.outputs = [str(output) for output in result.outputs]
        step_state.warnings = result.warnings

        if result.status == "manual_gate":
            step_state.status = "success"
            state.status = "partial"
            state.resumable_from = _next_step_id(workflow, step.id)
            state.manual_gate = {
                "step_id": step.id,
                "message": result.data.get("message") or result.message,
                "instructions": result.data.get("instructions", []),
                "next_actions": result.data.get("next_actions", []),
            }
            status_by_id[step.id] = "success"
            save_state(state)
            return

        step_state.status = result.status
        status_by_id[step.id] = step_state.status
        save_state(state)


def _skip_dependents(workflow: Workflow, state: RunState, failed_step_id: str, reason: str) -> None:
    pending = [failed_step_id]
    seen: set[str] = set()
    while pending:
        current = pending.pop()
        for step in workflow.steps:
            if step.id in seen or current not in step.needs:
                continue
            seen.add(step.id)
            step_state = state.step(step.id)
            if step_state.status in {"pending", "running"}:
                step_state.status = "skipped"
                step_state.reason = reason
                step_state.finished_at = now_iso()
            pending.append(step.id)


def _next_step_id(workflow: Workflow, current_id: str) -> str | None:
    ids = [step.id for step in workflow.steps]
    try:
        index = ids.index(current_id)
    except ValueError:
        return None
    return ids[index + 1] if index + 1 < len(ids) else None


def _final_status(state: RunState) -> str:
    statuses = [step.status for step in state.steps]
    if any(status == "failed" for status in statuses):
        return "failed"
    if any(status == "skipped" for status in statuses):
        return "partial"
    return "success"
