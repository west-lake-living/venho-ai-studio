from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from analytics_feedback.research_question_generator import generate_research_question_from_analytics
from strategy_memory.collect_pilot_evidence import collect_pilot_snapshots
from strategy_memory.pattern_inference import infer_strategy_pattern, promote_strategy_memory
from strategy_memory.qbsr_guardrail import qbsr_rate
from strategy_memory.stores import PromotedStrategyStore, StrategyBriefStore
from strategy_memory.weekly_brief import build_weekly_strategy_brief

app = typer.Typer(help="Module 09-adjacent Strategy Memory / Growth Intelligence pilot (Phase 7)")


@app.command("weekly-brief")
def weekly_brief_cmd(
    week_id: str = typer.Option(..., "--week-id", help='e.g. "2026-W32"'),
    baseline_qbsr: float = typer.Option(
        0.0, "--baseline-qbsr", help="Historical QBSR to guard candidate patterns against; 0.0 if no prior baseline period exists yet."
    ),
    min_sample_size: int = typer.Option(5, "--min-sample-size"),
    project: str = typer.Option("venho_hotel"),
    data_root: Path = typer.Option(Path("data/projects")),
    questions_root: Path = typer.Option(Path("research/questions")),
) -> None:
    """Build this week's advisory-only strategy brief from real pilot
    evidence (Phase 7). Every recommendation is `pending_approval` --
    nothing here is ever auto-applied to Knowledge Facts, content pillars,
    or automation policy; see `promote` for the separate, explicit
    founder-approval step required before anything counts as real strategy
    memory.

    Correctly returns 0 recommendations (every scope INCONCLUSIVE) until
    real pilot traffic + attributed inquiries accumulate past
    `--min-sample-size` publications per (pillar, platform) -- Growth Agent
    only went live 2026-08-03/04.

    Every INCONCLUSIVE scope also writes a real research question back into
    the Research OS vault (plan §14: "vòng phản hồi analytics ->
    research/questions/") -- `generate_research_question_from_analytics`
    already existed and is tested against this exact payload shape
    (id/status/scope/pattern), but until now was only ever called from
    M08AnalyticsBridge for per-publication observations, never for a
    strategy-pattern-level "why is this still inconclusive" question.
    """
    rows = collect_pilot_snapshots(project=project, data_root=data_root)
    scopes = sorted({(row["pillar"], row["platform"]) for row in rows})

    memories = []
    for pillar, platform in scopes:
        group_rows = [row for row in rows if row["pillar"] == pillar and row["platform"] == platform]
        memory = infer_strategy_pattern(
            group_rows,
            pattern=f"{platform} posts in pillar '{pillar}' drive qualified booking signals",
            scope={"pillar": pillar, "platform": platform},
            min_sample_size=min_sample_size,
        )
        memories.append(memory)
        if memory["status"] == "INCONCLUSIVE":
            try:
                generate_research_question_from_analytics(memory, root=questions_root)
            except Exception:  # noqa: BLE001 - a research-question write failure must not block the real brief
                pass

    total_qualified = sum(row["qualified_booking_signals"] for row in rows)
    total_reach = sum(row["eligible_reach"] for row in rows)
    candidate_qbsr = qbsr_rate(unique_qualified_booking_signals=total_qualified, eligible_reach=total_reach)

    brief = build_weekly_strategy_brief(
        week_id=week_id, memories=memories, baseline_qbsr=baseline_qbsr, candidate_qbsr=candidate_qbsr
    )
    StrategyBriefStore(project, data_root).save(week_id, brief)
    typer.echo(json.dumps(brief, ensure_ascii=False, indent=2))


@app.command("promote")
def promote_cmd(
    week_id: str = typer.Option(..., "--week-id"),
    pattern: str = typer.Option(..., "--pattern", help="Exact `pattern` text of the recommendation to promote (must match a real weekly-brief entry)."),
    approved_by: str = typer.Option(..., "--approved-by"),
    project: str = typer.Option("venho_hotel"),
    data_root: Path = typer.Option(Path("data/projects")),
) -> None:
    """Explicit founder approval step (plan §14 Phase 7: "advisory-only" --
    nothing from `weekly-brief` becomes real strategy memory without this).
    Only a recommendation that already exists in a real saved weekly brief
    can be promoted -- this command does not accept an ad-hoc pattern."""
    brief_store = StrategyBriefStore(project, data_root)
    brief = brief_store.load(week_id)
    if brief is None:
        typer.echo(json.dumps({"ok": False, "error": f"No weekly brief found for week_id={week_id}"}), err=True)
        raise typer.Exit(code=1)

    memory = next((rec for rec in brief["recommendations"] if rec["pattern"] == pattern), None)
    if memory is None:
        typer.echo(json.dumps({"ok": False, "error": f"No recommendation matching pattern={pattern!r} in week {week_id}"}), err=True)
        raise typer.Exit(code=1)

    try:
        promoted = promote_strategy_memory(memory, approved_by=approved_by)
    except ValueError as exc:
        typer.echo(json.dumps({"ok": False, "error": str(exc)}), err=True)
        raise typer.Exit(code=1)

    PromotedStrategyStore(project, data_root).save(f"{week_id}-{promoted['id']}", promoted)
    typer.echo(json.dumps({"ok": True, "promoted": promoted}, ensure_ascii=False, indent=2))


@app.command("list-promoted")
def list_promoted_cmd(project: str = typer.Option("venho_hotel"), data_root: Path = typer.Option(Path("data/projects"))) -> None:
    """Everything actually approved to date -- distinct from any given
    week's advisory brief, which may include un-promoted/rejected/expired
    recommendations."""
    typer.echo(json.dumps(PromotedStrategyStore(project, data_root).list_all(), ensure_ascii=False, indent=2))
