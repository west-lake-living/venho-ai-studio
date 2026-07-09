from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from automation_studio.action_registry import list_actions
from automation_studio.errors import AutomationError
from automation_studio.run_state import load_state
from automation_studio.workflow_loader import list_workflows, load_workflow
from automation_studio.workflow_runner import dry_run_workflow, run_workflow

app = typer.Typer(help="Automation Studio — run config-first workflows", add_completion=False)


@app.command("list")
def list_cmd() -> None:
    """List configured workflows."""
    workflows = list_workflows()
    if not workflows:
        typer.echo("No workflows found.")
        return
    for workflow in workflows:
        typer.echo(f"{workflow.workflow_id:<28} {workflow.name} (v{workflow.version})")


@app.command("actions")
def actions_cmd() -> None:
    """List registered module actions."""
    for spec in list_actions():
        required = ", ".join(spec.required) or "-"
        optional = ", ".join(spec.optional) or "-"
        typer.echo(f"{spec.key}")
        typer.echo(f"  required: {required}")
        typer.echo(f"  optional: {optional}")


@app.command("run")
def run_cmd(
    workflow_id: str = typer.Argument(..., help="Workflow ID, not file name"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Override workflow project"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate workflow without calling modules"),
) -> None:
    """Run a workflow by workflow_id."""
    try:
        workflow = load_workflow(workflow_id, project_override=project)
        if dry_run:
            dry_run_workflow(workflow)
            typer.secho("Dry-run OK.", fg=typer.colors.GREEN, bold=True)
            return
        state, report = run_workflow(workflow)
        _print_result(state.status, state.run_id, report)
    except AutomationError as exc:
        typer.secho(f"Automation error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    except Exception as exc:  # noqa: BLE001 - CLI should present clear top-level failures
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@app.command("resume")
def resume_cmd(run_id: str = typer.Argument(..., help="Run ID from data/automation_runs/state")) -> None:
    """Resume a failed or partial run from its resumable step."""
    try:
        previous = load_state(run_id)
        if not previous.resumable_from:
            typer.secho(f"Run {run_id} has no resumable_from step.", fg=typer.colors.YELLOW)
            return
        workflow = load_workflow(previous.workflow_id, project_override=previous.project)
        state, report = run_workflow(workflow, resume_from=previous.resumable_from)
        _print_result(state.status, state.run_id, report)
    except AutomationError as exc:
        typer.secho(f"Automation error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    except Exception as exc:  # noqa: BLE001
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


def _print_result(status: str, run_id: str, report: Optional[Path]) -> None:
    color = typer.colors.GREEN if status == "success" else typer.colors.YELLOW
    typer.secho(f"Automation run {status}: {run_id}", fg=color, bold=True)
    if report:
        typer.echo(f"  Report: {report}")
