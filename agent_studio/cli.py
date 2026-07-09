from __future__ import annotations

from pathlib import Path

import typer

from agent_studio.agents import BaseAgent
from agent_studio.renderers import render_response_json, render_response_markdown
from agent_studio.request_validator import validate_agent_request

app = typer.Typer(help="Module 09 Agent Studio")


@app.callback(invoke_without_command=True)
def run_agent(
    ctx: typer.Context,
    agent: str = typer.Option(None, "--agent"),
    project: str = typer.Option("venho_hotel", "--project"),
    goal: str = typer.Option(None, "--goal"),
    plan_only: bool = typer.Option(False, "--plan-only"),
    execute: bool = typer.Option(False, "--execute"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    data_root: Path = typer.Option(Path("data"), "--data-root"),
    config_root: Path = typer.Option(Path("config/projects"), "--config-root"),
    output_json: bool = typer.Option(False, "--json"),
) -> None:
    if ctx.invoked_subcommand is not None:
        return
    if not agent or not goal:
        raise typer.BadParameter("--agent and --goal are required")
    execution_mode = "execute" if execute else "dry_run" if dry_run else "plan_only"
    if plan_only:
        execution_mode = "plan_only"
    request = {
        "project": project,
        "agent": agent,
        "goal": goal,
        "execution_mode": execution_mode,
        "context": {"knowledge_refs": ["VENHO_BRAND_DNA", "VENHO_CONTENT_PILLARS", "VENHO_WESTLAKE_DNA"], "analytics_refs": ["latest_30d_advisory"]},
        "constraints": {"language": "vi", "validation_level": "strict", "max_steps": 5, "allow_external_actions": execute},
    }
    response = BaseAgent(config_root=config_root, data_root=data_root).run(request)
    typer.echo(render_response_json(response) if output_json else render_response_markdown(response))


@app.command("explain")
def explain(plan_id: str = typer.Option(..., "--plan-id"), project: str = typer.Option("venho_hotel", "--project")) -> None:
    typer.echo(f"Plan {plan_id} for {project}: inspect data/projects/{project}/agents/plans/{plan_id}.json when persistence is enabled.")


@app.command("validate")
def validate(request_file: Path) -> None:
    request = validate_agent_request(__import__("json").loads(request_file.read_text(encoding="utf-8")))
    typer.echo(f"Valid agent request: {request.agent} / {request.project}")


if __name__ == "__main__":
    app()
