from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import typer

from growth_orchestrator.application.approve_and_dispatch import approve_and_dispatch, list_pending
from growth_orchestrator.application.daily_cycle import CADENCE_DAYS, run_daily_cycle
from growth_orchestrator.application.measure_publication import measure_publication
from growth_orchestrator.application.reconcile_publication import reconcile_publication
from growth_orchestrator.application.run_blog_pipeline import run_blog_pipeline
from growth_orchestrator.application.run_content_pipeline import run_content_pipeline
from growth_orchestrator.application.weekly_cycle import run_weekly_cycle

app = typer.Typer(help="Ven Ho Growth Orchestrator")


@app.command("run")
def run(brief_file: Path) -> None:
    package = run_content_pipeline(json.loads(brief_file.read_text(encoding="utf-8")))
    typer.echo(json.dumps(package, ensure_ascii=False, indent=2))


@app.command("daily-cycle")
def daily_cycle(
    day: Optional[str] = typer.Option(None, help="Cadence day (monday/wednesday/friday/saturday). Defaults to today (Asia/Ho_Chi_Minh)."),
    project: str = typer.Option("venho_hotel"),
    generate_image: bool = typer.Option(True, "--image/--no-image", help="Set --no-image to skip photo generation (e.g. OPENAI_API_KEY unavailable/invalid)."),
) -> None:
    """Generate this cadence day's drafts and queue them PENDING_APPROVAL (does not publish).

    Meant to run on the T2/T4/T6/T7 8AM cron -- actual publishing only
    happens later when a human approves on VENHO OS Dashboard. Text and
    images must both pass real Validator scoring (see M03ValidatorBridge /
    validator_studio.image_validator, provider="openai") before queuing --
    a failed draft is regenerated automatically, see daily_cycle's
    MAX_TEXT_ATTEMPTS/MAX_IMAGE_ATTEMPTS.
    """
    resolved_day = day or datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%A").lower()
    if resolved_day not in CADENCE_DAYS:
        typer.echo(f"'{resolved_day}' is not a cadence day ({sorted(CADENCE_DAYS)}); nothing to do today.")
        raise typer.Exit(code=0)
    result = run_daily_cycle(
        resolved_day, project=project, generate_image=generate_image, image_validation_provider="openai"
    )
    typer.echo(json.dumps({"day": result.day, "topic": result.topic, "publications": result.publications}, ensure_ascii=False, indent=2))


@app.command("weekly-cycle")
def weekly_cycle(
    project: str = typer.Option("venho_hotel"),
    generate_image: bool = typer.Option(True, "--image/--no-image", help="Set --no-image to skip photo generation (e.g. OPENAI_API_KEY unavailable/invalid)."),
) -> None:
    """Generate a full week's cadence (Mon/Wed/Fri/Sat) in one run and queue
    all of it PENDING_APPROVAL, so Harry can review/approve the whole week in
    one VENHO OS Dashboard session instead of one cadence day at a time.

    Meant to run on a single weekly cron tick (see
    .github/workflows/growth-daily-cycle.yml) -- does not publish anything.
    Text and images must both pass real Validator scoring before queuing --
    a failed draft is regenerated automatically (see daily_cycle's
    MAX_TEXT_ATTEMPTS/MAX_IMAGE_ATTEMPTS).
    """
    result = run_weekly_cycle(
        project=project, generate_image=generate_image, image_validation_provider="openai"
    )
    typer.echo(
        json.dumps(
            {
                "days": [
                    {"day": day.day, "topic": day.topic, "publications": day.publications}
                    for day in result.days
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
    )


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


@app.command("blog")
def blog_cmd(
    topic: str = typer.Option(..., "--topic"),
    keyword: Optional[str] = typer.Option(None, "--keyword"),
    dna_subject: str = typer.Option("westlake", "--dna-subject"),
    project: str = typer.Option("venho_hotel"),
) -> None:
    """Generate a blog/SEO draft grounded in Research OS approved facts
    (DoD #11). Manually invoked -- no scheduled blog cadence exists yet.
    """
    result = run_blog_pipeline(topic, keyword=keyword, dna_subject=dna_subject, project=project)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@app.command("reconcile")
def reconcile_cmd(
    publication_id: str = typer.Option(..., "--publication-id"),
    platform_post_id: str = typer.Option(..., "--platform-post-id"),
    reconciled_by: str = typer.Option(..., "--reconciled-by"),
    permalink: Optional[str] = typer.Option(None, "--permalink"),
    project: str = typer.Option("venho_hotel"),
) -> None:
    """Manually record that a dispatched (GATEWAY_ACCEPTED) publication went
    live for real -- no automatic Make.com callback receiver exists yet, so
    this is the operator's reconciliation step after checking the real post.
    Required before `measure` can observe anything (see DoD #3).
    """
    try:
        result = reconcile_publication(
            publication_id,
            platform_post_id=platform_post_id,
            reconciled_by=reconciled_by,
            permalink=permalink,
            project=project,
        )
    except (KeyError, ValueError) as exc:
        typer.echo(json.dumps({"ok": False, "error": str(exc)}), err=True)
        raise typer.Exit(code=1)
    typer.echo(json.dumps({"ok": True, "publication": result}, ensure_ascii=False, indent=2))


@app.command("measure")
def measure_cmd(
    publication_id: str = typer.Option(..., "--publication-id"),
    project: str = typer.Option("venho_hotel"),
) -> None:
    """Collect + score performance for a PUBLISHED publication (M08 Analytics)."""
    try:
        result = measure_publication(publication_id)
    except KeyError as exc:
        typer.echo(json.dumps({"ok": False, "error": str(exc)}), err=True)
        raise typer.Exit(code=1)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@app.command("version")
def version() -> None:
    typer.echo("growth_orchestrator 0.1.0")


if __name__ == "__main__":
    app()
