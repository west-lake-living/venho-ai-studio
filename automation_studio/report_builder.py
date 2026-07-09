from __future__ import annotations

from pathlib import Path

from automation_studio.paths import REPORT_DIR
from automation_studio.run_state import RunState
from automation_studio.workflow_loader import Workflow


def build_report(state: RunState, workflow: Workflow) -> str:
    lines: list[str] = [
        "# AUTOMATION RUN REPORT",
        "",
        "## META",
        f"- Run ID: `{state.run_id}`",
        f"- Status: `{state.status}`",
        f"- Project: `{state.project or '-'}`",
        f"- Started: `{state.started_at}`",
        f"- Finished: `{state.finished_at or '-'}`",
        "",
        "## WORKFLOW",
        f"- ID: `{workflow.workflow_id}`",
        f"- Name: {workflow.name}",
        f"- Version: `{workflow.version}`",
        f"- Source: `{workflow.source_path}`",
        "",
        "## INPUTS",
    ]
    for step in workflow.steps:
        lines.append(f"- `{step.id}`: `{step.action_key}` params={step.params}")

    lines.extend(["", "## STEPS EXECUTED"])
    for step in state.steps:
        reason = f" — {step.reason}" if step.reason else ""
        lines.append(f"- `{step.id}`: `{step.status}`{reason} (attempts: {step.attempts})")
        for output in step.outputs:
            lines.append(f"  - output: `{output}`")
        for warning in step.warnings:
            lines.append(f"  - warning: {warning}")

    lines.extend(["", "## MANUAL GATE"])
    if state.manual_gate:
        lines.append(f"- Step: `{state.manual_gate.get('step_id')}`")
        lines.append(f"- Message: {state.manual_gate.get('message')}")
        for item in state.manual_gate.get("instructions", []):
            lines.append(f"- {item}")
    else:
        lines.append("- None")

    lines.extend(["", "## OUTPUTS"])
    outputs = [output for step in state.steps for output in step.outputs]
    if outputs:
        lines.extend(f"- `{output}`" for output in outputs)
    else:
        lines.append("- None")

    lines.extend(["", "## WARNINGS"])
    warnings = list(state.warnings)
    for step in state.steps:
        warnings.extend(step.warnings)
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- None")

    lines.extend(["", "## FAILED ITEMS"])
    failed = [step for step in state.steps if step.status == "failed"]
    if failed:
        lines.extend(f"- `{step.id}`: {step.reason or 'failed'}" for step in failed)
    else:
        lines.append("- None")

    lines.extend(["", "## NEXT ACTIONS"])
    if state.manual_gate:
        next_actions = state.manual_gate.get("next_actions") or []
        lines.extend(f"- {item}" for item in next_actions)
    elif state.resumable_from:
        lines.append(f"- Run `venho auto resume {state.run_id}` after fixing `{state.resumable_from}`.")
    else:
        lines.append("- None")

    return "\n".join(lines) + "\n"


def write_report(state: RunState, workflow: Workflow, report_dir: Path = REPORT_DIR) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"{state.run_id}.md"
    path.write_text(build_report(state, workflow), encoding="utf-8")
    return path

