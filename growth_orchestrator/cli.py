from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import typer

from growth_orchestrator.application.approve_and_dispatch import (
    approve_and_dispatch,
    edit_publication,
    list_pending,
    reject_publication,
    retry_dispatch,
)
from growth_orchestrator.application.daily_cycle import CADENCE_DAYS, run_daily_cycle
from growth_orchestrator.application.measure_publication import measure_publication
from growth_orchestrator.application.reconcile_publication import reconcile_publication
from growth_orchestrator.application.run_blog_pipeline import run_blog_pipeline
from growth_orchestrator.application.run_content_pipeline import run_content_pipeline
from growth_orchestrator.application.weekly_cycle import run_weekly_cycle
from shared.jobs.slot_store import SlotStore

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
    typer.echo(json.dumps({"day": result.day, "topic": result.topic, "publications": result.publications, "errors": result.errors}, ensure_ascii=False, indent=2))


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
                "skipped_already_run": result.skipped_already_run,
                "days": [
                    {"day": day.day, "topic": day.topic, "publications": day.publications, "errors": day.errors}
                    for day in result.days
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


@app.command("slots")
def slots_cmd(
    project: str = typer.Option("venho_hotel"),
    weeks_ahead: int = typer.Option(1, help="How many ISO weeks from today to show (1 = this week only)."),
) -> None:
    """Read-only view of PublishingSlot state for the dashboard/CLI operator
    -- which cadence slots got filled, which are still pending, which were
    missed. See shared.jobs.slot_store.SlotStore / growth_orchestrator.
    domain.publishing_slot.PublishingSlot (plan v3.1 §4.4)."""
    from datetime import date, timedelta

    from growth_orchestrator.application.weekly_cycle import WEEKLY_CADENCE_ORDER, _next_occurrence

    slot_store = SlotStore(db_path=Path("data/projects") / project / "growth" / "growth.db")
    today = date.today()
    rows = []
    for week_offset in range(weeks_ahead):
        week_start = today + timedelta(days=7 * week_offset)
        for day in WEEKLY_CADENCE_ORDER:
            slot_date = _next_occurrence(day, on_or_after=week_start)
            slot = slot_store.get(f"slot-{slot_date.isoformat()}-{day}")
            rows.append(
                {
                    "slot_date": slot_date.isoformat(),
                    "day": day,
                    "status": slot.status if slot else "NOT_CREATED",
                    "content_package_id": slot.content_package_id if slot else None,
                }
            )
    typer.echo(json.dumps(rows, ensure_ascii=False, indent=2))


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


@app.command("reject")
def reject_cmd(
    publication_id: str = typer.Option(..., "--publication-id"),
    rejected_by: str = typer.Option(..., "--rejected-by"),
    reason: Optional[str] = typer.Option(None, "--reason"),
    project: str = typer.Option("venho_hotel"),
) -> None:
    """Reject a PENDING_APPROVAL publication -- no dispatch, no webhook call.

    What the "Từ chối" button on VENHO OS Dashboard's Publishing & Schedule
    section calls (via a local `venho-growth` subprocess). Rejected rows drop
    out of `list-pending` automatically.
    """
    try:
        result = reject_publication(publication_id, rejected_by=rejected_by, reason=reason, project=project)
    except (KeyError, ValueError) as exc:
        typer.echo(json.dumps({"ok": False, "error": str(exc)}), err=True)
        raise typer.Exit(code=1)
    typer.echo(json.dumps({"ok": True, "publication": result}, ensure_ascii=False, indent=2))


@app.command("retry-dispatch")
def retry_dispatch_cmd(
    publication_id: str = typer.Option(..., "--publication-id"),
    project: str = typer.Option("venho_hotel"),
) -> None:
    """Re-fire the Make.com dispatch for a publication stranded in GATEWAY_ERROR
    (e.g. a transient webhook/network failure on the first approve). Reuses
    the original approval -- does not ask for approved_by again.
    """
    try:
        result = retry_dispatch(publication_id, project=project)
    except (KeyError, ValueError) as exc:
        typer.echo(json.dumps({"ok": False, "error": str(exc)}), err=True)
        raise typer.Exit(code=1)
    typer.echo(json.dumps({"ok": True, "publication": result}, ensure_ascii=False, indent=2))


@app.command("edit")
def edit_cmd(
    publication_id: str = typer.Option(..., "--publication-id"),
    edited_by: str = typer.Option(..., "--edited-by"),
    text_file: Path = typer.Option(..., "--text-file", help="Path to a UTF-8 file containing the edited copy."),
    project: str = typer.Option("venho_hotel"),
) -> None:
    """Edit a PENDING_APPROVAL/GATEWAY_ERROR publication's copy and re-run the
    real content Validator gate. Only a fresh APPROVE re-enters the approval
    queue; anything else lands on NEEDS_REVISION. Clears any prior approval
    -- a later Approve always snapshots the edited content, never the old one.
    """
    try:
        new_text = text_file.read_text(encoding="utf-8")
        result = edit_publication(publication_id, edited_by=edited_by, new_text=new_text, project=project)
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


@app.command("trend-scan")
def trend_scan_cmd(
    project: str = typer.Option("venho_hotel"),
    config_root: Path = typer.Option(Path("config/projects/venho_hotel/research")),
) -> None:
    """Real Tavily search -> Gemini Flash classification -> scan_trends
    scoring for the Saturday special lane, merged into trend_candidates.json
    as unapproved proposals. Requires TAVILY_API_KEY + GEMINI_API_KEY in
    env; does not queue/publish anything and does not skip human approval
    (brand_safety.yaml's `human_approval: mandatory`) -- see `trend-approve`.
    """
    import os

    import yaml

    from research_engine.trend_radar.application.fetch_saturday_candidates import fetch_and_score_saturday_candidates
    from research_engine.trend_radar.trend_candidate_store import TrendCandidateStore

    tavily_api_key = os.environ.get("TAVILY_API_KEY", "")
    if not tavily_api_key:
        typer.echo(json.dumps({"ok": False, "error": "TAVILY_API_KEY not set"}), err=True)
        raise typer.Exit(code=1)
    trend_policy = yaml.safe_load((config_root / "trend_policy.yaml").read_text(encoding="utf-8"))
    safety_policy = yaml.safe_load((config_root / "brand_safety.yaml").read_text(encoding="utf-8"))
    scored = fetch_and_score_saturday_candidates(tavily_api_key=tavily_api_key, trend_policy=trend_policy, safety_policy=safety_policy)
    inserted = TrendCandidateStore(project).merge_new(scored)
    typer.echo(json.dumps({"ok": True, "scanned": len(scored), "inserted_new": inserted}, ensure_ascii=False, indent=2))


@app.command("trend-list")
def trend_list_cmd(project: str = typer.Option("venho_hotel")) -> None:
    """List all Trend Radar candidates (approved and pending) for review."""
    from research_engine.trend_radar.trend_candidate_store import TrendCandidateStore

    typer.echo(json.dumps(TrendCandidateStore(project).load(), ensure_ascii=False, indent=2))


@app.command("trend-approve")
def trend_approve_cmd(
    candidate_id: str = typer.Option(..., "--candidate-id"),
    approved_by: str = typer.Option(..., "--approved-by"),
    project: str = typer.Option("venho_hotel"),
) -> None:
    """Mark one scanned trend candidate verified_by_human=True -- required
    before it can ever be picked as a Saturday topic (see _pick_topic in
    daily_cycle.py). This is the human-approval gate brand_safety.yaml
    mandates; nothing in trend-scan can skip it."""
    from research_engine.trend_radar.trend_candidate_store import TrendCandidateStore

    try:
        result = TrendCandidateStore(project).approve(candidate_id, approved_by=approved_by)
    except KeyError as exc:
        typer.echo(json.dumps({"ok": False, "error": str(exc)}), err=True)
        raise typer.Exit(code=1)
    typer.echo(json.dumps({"ok": True, "candidate": result}, ensure_ascii=False, indent=2))


@app.command("version")
def version() -> None:
    typer.echo("growth_orchestrator 0.1.0")


if __name__ == "__main__":
    app()
