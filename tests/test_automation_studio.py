from __future__ import annotations

from pathlib import Path

import pytest

from automation_studio.action_registry import ActionSpec, REGISTRY
from automation_studio.errors import ActionRegistryError, WorkflowConfigError, WorkflowLockError
from automation_studio.run_lock import RunLock
from automation_studio.scheduler import parse_scheduler_plan
from automation_studio.types import StepResult
from automation_studio.workflow_loader import load_workflow_file
from automation_studio.workflow_runner import dry_run_workflow, run_workflow


def _workflow_file(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "workflow.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def test_loader_validates_unknown_need(tmp_path: Path) -> None:
    path = _workflow_file(
        tmp_path,
        """
workflow_id: bad
name: Bad
version: "1.0"
steps:
  - id: one
    module: automation
    action: manual_gate
    needs: [missing]
    params: { message: pause }
""",
    )
    with pytest.raises(WorkflowConfigError, match="unknown"):
        load_workflow_file(path)


def test_dry_run_rejects_missing_required_param(tmp_path: Path) -> None:
    path = _workflow_file(
        tmp_path,
        """
workflow_id: bad_params
name: Bad Params
version: "1.0"
steps:
  - id: one
    module: automation
    action: manual_gate
    params: {}
""",
    )
    workflow = load_workflow_file(path)
    with pytest.raises(ActionRegistryError, match="missing required"):
        dry_run_workflow(workflow)


def test_manual_gate_creates_partial_state_and_report(tmp_path: Path) -> None:
    path = _workflow_file(
        tmp_path,
        """
workflow_id: gate
name: Gate
version: "1.0"
steps:
  - id: pause
    module: automation
    action: manual_gate
    params:
      message: make an image
      instructions: [save the generated image]
      next_actions: [run validation]
""",
    )
    workflow = load_workflow_file(path)

    state, report = run_workflow(workflow)

    assert state.status == "partial"
    assert state.manual_gate is not None
    assert state.manual_gate["step_id"] == "pause"
    assert report is not None
    assert "## MANUAL GATE" in report.read_text(encoding="utf-8")


def test_skip_dependents_on_failed_step(tmp_path: Path) -> None:
    def fail_action() -> StepResult:
        raise RuntimeError("planned failure")

    REGISTRY["test.fail"] = ActionSpec(key="test.fail", handler=fail_action)
    try:
        path = _workflow_file(
            tmp_path,
            """
workflow_id: skip_flow
name: Skip Flow
version: "1.0"
steps:
  - id: fail
    module: test
    action: fail
    params: {}
    on_error: skip_dependents
  - id: dependent
    module: automation
    action: manual_gate
    needs: [fail]
    params: { message: should not run }
""",
        )
        workflow = load_workflow_file(path)
        state, _report = run_workflow(workflow)
        statuses = {step.id: step.status for step in state.steps}
        assert statuses["fail"] == "failed"
        assert statuses["dependent"] == "skipped"
    finally:
        REGISTRY.pop("test.fail", None)


def test_run_lock_refuses_existing_lock(tmp_path: Path) -> None:
    lock = RunLock("same_workflow", lock_dir=tmp_path)
    lock.acquire("run_one")
    try:
        with pytest.raises(WorkflowLockError, match="already running"):
            lock.acquire("run_two")
    finally:
        lock.release()


def test_resume_treats_previous_steps_as_dependency_satisfied(tmp_path: Path) -> None:
    calls: list[str] = []

    def mark_action(name: str) -> StepResult:
        calls.append(name)
        return StepResult(status="success")

    REGISTRY["test.mark"] = ActionSpec(key="test.mark", handler=mark_action, required=("name",))
    try:
        path = _workflow_file(
            tmp_path,
            """
workflow_id: resume_flow
name: Resume Flow
version: "1.0"
steps:
  - id: one
    module: test
    action: mark
    params: { name: one }
  - id: two
    module: test
    action: mark
    needs: [one]
    params: { name: two }
""",
        )
        workflow = load_workflow_file(path)
        state, _report = run_workflow(workflow, resume_from="two")
        statuses = {step.id: step.status for step in state.steps}
        assert statuses["one"] == "skipped"
        assert statuses["two"] == "success"
        assert calls == ["two"]
    finally:
        REGISTRY.pop("test.mark", None)


def test_scheduler_parses_but_stays_disabled(tmp_path: Path) -> None:
    path = _workflow_file(
        tmp_path,
        """
workflow_id: scheduled
name: Scheduled
version: "1.0"
trigger:
  type: schedule
  cron: "0 8 * * *"
steps:
  - id: pause
    module: automation
    action: manual_gate
    params: { message: pause }
""",
    )
    workflow = load_workflow_file(path)
    plan = parse_scheduler_plan(workflow)
    assert plan.trigger_type == "schedule"
    assert plan.enabled is False
    assert "disabled in MVP" in plan.message
