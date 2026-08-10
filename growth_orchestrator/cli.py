from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import typer

from growth_orchestrator.application.approve_and_dispatch import (
    approve_and_dispatch,
    approve_week,
    edit_publication,
    list_pending,
    reject_publication,
    retry_dispatch,
)
from growth_orchestrator.application.scheduled_dispatch import dispatch_due
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
    # Bind this run to a real PublishingSlot. Without both slot_store and
    # slot_date, run_daily_cycle records `slot_id=None` on every publication
    # it queues, and `_advance_slot_on_dispatch_success` then has nothing to
    # advance on approval -- which is why 102 registry rows carried no slot_id
    # and the cadence table could never evidence DoD #9. weekly-cycle always
    # passed these; the daily CLI never did.
    from growth_orchestrator.application.weekly_cycle import _next_occurrence

    slot_date = _next_occurrence(resolved_day, on_or_after=datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date())
    result = run_daily_cycle(
        resolved_day,
        project=project,
        generate_image=generate_image,
        image_validation_provider="openai",
        slot_store=SlotStore(db_path=Path("data/projects") / project / "growth" / "growth.db"),
        slot_date=slot_date.isoformat(),
    )
    typer.echo(json.dumps({"day": result.day, "topic": result.topic, "publications": result.publications, "errors": result.errors}, ensure_ascii=False, indent=2))


@app.command("weekly-cycle")
def weekly_cycle(
    project: str = typer.Option("venho_hotel"),
    generate_image: bool = typer.Option(True, "--image/--no-image", help="Set --no-image to skip photo generation (e.g. OPENAI_API_KEY unavailable/invalid)."),
    platforms: list[str] = typer.Option(["facebook", "instagram"], "--platform", help="Required platform(s) for every cadence slot."),
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
        project=project, platforms=platforms, generate_image=generate_image, image_validation_provider="openai"
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


@app.command("ensure-slots")
def ensure_slots_cmd(
    project: str = typer.Option("venho_hotel"),
    horizon_days: Optional[int] = typer.Option(None, "--horizon-days", help="Override cadence_policy.slot_creation_horizon_days."),
) -> None:
    """Materialise the rolling horizon of OPEN PublishingSlots (DoD #9).

    `weekly-cycle` does this itself on every real run; this exposes it
    standalone so the horizon can be (re)created without spending a content
    run's API budget -- e.g. after a gap in the cron, or to seed the table
    on a machine that has never run a full week."""
    from growth_orchestrator.application.manage_slots import ensure_slot_horizon

    typer.echo(json.dumps(ensure_slot_horizon(project=project, horizon_days=horizon_days), ensure_ascii=False, indent=2))


@app.command("backup")
def backup_cmd(
    project: str = typer.Option("venho_hotel"),
    dest: Optional[Path] = typer.Option(None, "--dest", help="Backup root (default: $VENHO_BACKUP_DIR or ~/VenHo-Backups/venho-ai-studio)."),
    keep: int = typer.Option(30, "--keep", help="Snapshots to retain before pruning."),
    verify: bool = typer.Option(True, "--verify/--no-verify", help="Restore + check the snapshot immediately after taking it."),
) -> None:
    """Snapshot growth state -- database, registry, facts, photos -- and prove
    it restores (DoD #24).

    `data/` is gitignored in full, so nothing here was ever covered by the
    "git is our backup" assumption. Alerts Telegram if the verify fails: a
    backup that silently stopped restoring is worse than no backup, because
    it stops anyone from noticing."""
    from shared.backup.growth_backup import create_backup, prune_backups, verify_restore

    manifest = create_backup(project=project, backup_dir=dest)
    result: dict = {
        "snapshot_dir": manifest["snapshot_dir"],
        "counts": manifest["counts"],
        "database_row_counts": (manifest.get("database") or {}).get("row_counts"),
    }
    if verify:
        report = verify_restore(Path(manifest["snapshot_dir"]), backup_dir=dest)
        result["verify"] = report
        if not report["ok"]:
            import os

            from shared.notify.telegram import send_alert, telegram_notifier_or_mock_from_env

            chat_id = os.environ.get("TELEGRAM_CHAT_ID")
            if chat_id:
                send_alert(
                    "backup_verify_failed",
                    f"VENHO Growth backup verify FAILED: {'; '.join(report['errors'][:3])}",
                    notifier=telegram_notifier_or_mock_from_env(os.environ),
                    chat_id=chat_id,
                )
    result["prune"] = prune_backups(project=project, backup_dir=dest, keep=keep)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))
    if verify and not result["verify"]["ok"]:
        raise typer.Exit(code=1)


@app.command("backup-verify")
def backup_verify_cmd(
    project: str = typer.Option("venho_hotel"),
    snapshot: Optional[Path] = typer.Option(None, "--snapshot", help="Snapshot directory (default: the most recent one)."),
    dest: Optional[Path] = typer.Option(None, "--dest"),
) -> None:
    """Restore an existing snapshot into a scratch directory and verify it."""
    from shared.backup.growth_backup import latest_backup, verify_restore

    target = snapshot or latest_backup(project=project, backup_dir=dest)
    if target is None:
        typer.echo(json.dumps({"ok": False, "error": "no backups found"}, ensure_ascii=False))
        raise typer.Exit(code=1)
    report = verify_restore(Path(target), backup_dir=dest)
    typer.echo(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["ok"]:
        raise typer.Exit(code=1)


@app.command("list-pending")
def list_pending_cmd(project: str = typer.Option("venho_hotel")) -> None:
    """List PENDING_APPROVAL publications for the VENHO OS Dashboard review table."""
    typer.echo(json.dumps(list_pending(project=project), ensure_ascii=False, indent=2))


@app.command("approve-and-dispatch")
def approve_and_dispatch_cmd(
    publication_id: str = typer.Option(..., "--publication-id"),
    approved_by: str = typer.Option(..., "--approved-by"),
    project: str = typer.Option("venho_hotel"),
    allow_shadow: bool = typer.Option(
        False, "--allow-shadow", help="Publish this row even though the rollout stage is still shadow. Recorded on the row as shadow_override_by."
    ),
) -> None:
    """Retired unsafe command; publishing is now scheduler-only."""
    typer.echo(json.dumps({"ok": False, "error": "approve-and-dispatch retired; use approve-week then dispatch-due"}), err=True)
    raise typer.Exit(code=2)


@app.command("approve-week")
def approve_week_cmd(
    approved_by: str = typer.Option(..., "--approved-by"),
    week_start: Optional[str] = typer.Option(None, "--week-start", help="Monday date, YYYY-MM-DD. Defaults to this week in Asia/Ho_Chi_Minh."),
    project: str = typer.Option("venho_hotel"),
) -> None:
    """Record one approval for every pending post in a scheduled week.

    It never dispatches to Make.com.  A later scheduler releases each
    APPROVED_SCHEDULED post at its own publishing slot.
    """
    today = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()
    try:
        resolved_week_start = date.fromisoformat(week_start) if week_start else (today - timedelta(days=today.weekday()))
    except ValueError as exc:
        typer.echo(json.dumps({"ok": False, "error": "week-start must be YYYY-MM-DD"}), err=True)
        raise typer.Exit(code=1) from exc
    if resolved_week_start.weekday() != 0:
        typer.echo(json.dumps({"ok": False, "error": "week-start must be a Monday"}), err=True)
        raise typer.Exit(code=1)
    try:
        publications = approve_week(approved_by=approved_by, week_start=resolved_week_start, project=project)
    except (KeyError, ValueError) as exc:
        typer.echo(json.dumps({"ok": False, "error": str(exc)}), err=True)
        raise typer.Exit(code=1)
    typer.echo(json.dumps({"ok": True, "week_start": resolved_week_start.isoformat(), "publications": publications}, ensure_ascii=False, indent=2))


@app.command("dispatch-due")
def dispatch_due_cmd(
    project: str = typer.Option("venho_hotel"),
    limit: int = typer.Option(50, min=1, max=200),
    allow_shadow: bool = typer.Option(False, "--allow-shadow"),
    catch_up_today: bool = typer.Option(False, "--catch-up-today"),
) -> None:
    """Scheduler entrypoint: dispatch only APPROVED_SCHEDULED rows now due."""
    try:
        publications = dispatch_due(
            project=project,
            limit=limit,
            allow_shadow=allow_shadow,
            catch_up_today=catch_up_today,
        )
    except (KeyError, ValueError) as exc:
        typer.echo(json.dumps({"ok": False, "error": str(exc)}), err=True)
        raise typer.Exit(code=1)
    typer.echo(json.dumps({"ok": True, "publications": publications}, ensure_ascii=False, indent=2))


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
    allow_shadow: bool = typer.Option(
        False, "--allow-shadow", help="Release this row even though the rollout stage is still shadow."
    ),
) -> None:
    """Re-fire the Make.com dispatch for a publication stranded in GATEWAY_ERROR
    (e.g. a transient webhook/network failure on the first approve) or parked
    on SHADOW_HELD by the rollout gate. Reuses the original approval -- does
    not ask for approved_by again.
    """
    try:
        result = retry_dispatch(publication_id, project=project, allow_shadow=allow_shadow)
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


@app.command("evergreen-add")
def evergreen_add_cmd(
    publication_id: str = typer.Option(..., "--publication-id", help="An existing publication row to promote into the pool."),
    added_by: str = typer.Option(..., "--added-by"),
    project: str = typer.Option("venho_hotel"),
) -> None:
    """Curate a real, already-dispatched publication into the Evergreen Pool
    (PB-004). Nothing is invented here -- only a human-picked existing
    publication row can enter the pool; see `EvergreenPoolStore.add_from_publication`.
    """
    from publishing_gateway.publication_registry import PublicationRegistry
    from shared.storage.evergreen_pool_store import EvergreenPoolStore

    registry = PublicationRegistry(project)
    match = next((p for p in registry.load()["publications"] if p.get("publication_id") == publication_id), None)
    if match is None:
        typer.echo(json.dumps({"ok": False, "error": f"Unknown publication_id: {publication_id}"}), err=True)
        raise typer.Exit(code=1)
    item = EvergreenPoolStore(project).add_from_publication(match, added_by=added_by)
    typer.echo(json.dumps({"ok": True, "item": item}, ensure_ascii=False, indent=2))


@app.command("evergreen-list")
def evergreen_list_cmd(project: str = typer.Option("venho_hotel")) -> None:
    """List everything currently in the Evergreen Pool (PB-004)."""
    from shared.storage.evergreen_pool_store import EvergreenPoolStore

    typer.echo(json.dumps(EvergreenPoolStore(project).list_items(), ensure_ascii=False, indent=2))


@app.command("check-runway")
def check_runway_cmd(
    project: str = typer.Option("venho_hotel"),
    horizon_days: int = typer.Option(14, "--horizon-days"),
) -> None:
    """On-demand runway check (PB-003) -- same logic `weekly-cycle` runs
    automatically at the end of every real run, exposed standalone so Harry
    (or a debug session) can check the queue's buffer without waiting for
    the next cron tick. Fires the real Telegram alert if TELEGRAM_BOT_TOKEN/
    TELEGRAM_CHAT_ID are set and the runway is critical/empty."""
    from growth_orchestrator.application.manage_queue import check_runway

    result = check_runway(project=project, horizon_days=horizon_days)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


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


@app.command("trend-reject")
def trend_reject_cmd(
    candidate_id: str = typer.Option(..., "--candidate-id"),
    rejected_by: str = typer.Option(..., "--rejected-by"),
    project: str = typer.Option("venho_hotel"),
) -> None:
    """Take one scanned trend candidate out of circulation permanently.

    The row stays in the file as a tombstone so the next Friday scan does not
    re-propose it (merge_new dedupes on id); it is gone from the dashboard and
    can never reach a Saturday brief."""
    from research_engine.trend_radar.trend_candidate_store import TrendCandidateStore

    try:
        result = TrendCandidateStore(project).reject(candidate_id, rejected_by=rejected_by)
    except KeyError as exc:
        typer.echo(json.dumps({"ok": False, "error": str(exc)}), err=True)
        raise typer.Exit(code=1)
    typer.echo(json.dumps({"ok": True, "candidate": result}, ensure_ascii=False, indent=2))


@app.command("version")
def version() -> None:
    typer.echo("growth_orchestrator 0.1.0")


if __name__ == "__main__":
    app()
