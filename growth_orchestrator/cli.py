from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import typer

from growth_orchestrator.application.approve_and_dispatch import approve_and_dispatch, list_pending
from growth_orchestrator.application.daily_cycle import CADENCE_DAYS, run_daily_cycle
from growth_orchestrator.application.run_content_pipeline import run_content_pipeline

app = typer.Typer(help="Ven Ho Growth Orchestrator")


@app.command("run")
def run(brief_file: Path) -> None:
    package = run_content_pipeline(json.loads(brief_file.read_text(encoding="utf-8")))
    typer.echo(json.dumps(package, ensure_ascii=False, indent=2))


@app.command("daily-cycle")
def daily_cycle(
    day: Optional[str] = typer.Option(None, help="Cadence day (monday/wednesday/friday/saturday). Defaults to today (Asia/Ho_Chi_Minh)."),
    project: str = typer.Option("venho_hotel"),
) -> None:
    """Generate this cadence day's drafts and queue them PENDING_APPROVAL (does not publish).

    Meant to run on the T2/T4/T6/T7 8AM cron -- actual publishing only
    happens later when a human approves on VENHO OS Dashboard.
    """
    resolved_day = day or datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%A").lower()
    if resolved_day not in CADENCE_DAYS:
        typer.echo(f"'{resolved_day}' is not a cadence day ({sorted(CADENCE_DAYS)}); nothing to do today.")
        raise typer.Exit(code=0)
    result = run_daily_cycle(resolved_day, project=project)
    typer.echo(json.dumps({"day": result.day, "topic": result.topic, "publications": result.publications}, ensure_ascii=False, indent=2))


@app.command("list-pending")
def list_pending_cmd(project: str = typer.Option("venho_hotel")) -> None:
    """List PENDING_APPROVAL publications for the VENHO OS Dashboard review table."""
    typer.echo(json.dumps(list_pending(project=project), ensure_ascii=False, indent=2))


@app.command("approve-and-dispatch")
def approve_and_dispatch_cmd(
    publication_id: str = typer.Option(..., "--publication-id"),
    approved_by: str = typer.Option(..., "--approved-by"),
    project: str = typer.Option("venho_hotel"),
) -> None:
    """Approve a PENDING_APPROVAL publication and fire the real Make.com webhook dispatch.

    This is what the "Approve" button on VENHO OS Dashboard's Publishing &
    Schedule section calls (via a local `venho-growth` subprocess) right after
    the click -- see growth_orchestrator/application/approve_and_dispatch.py.
    """
    try:
        result = approve_and_dispatch(publication_id, approved_by=approved_by, project=project)
    except (KeyError, ValueError) as exc:
        typer.echo(json.dumps({"ok": False, "error": str(exc)}), err=True)
        raise typer.Exit(code=1)
    typer.echo(json.dumps({"ok": True, "publication": result}, ensure_ascii=False, indent=2))


@app.command("version")
def version() -> None:
    typer.echo("growth_orchestrator 0.1.0")


if __name__ == "__main__":
    app()
