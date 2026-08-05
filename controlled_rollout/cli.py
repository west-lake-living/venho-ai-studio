from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from controlled_rollout.collect_real_scorecard_metrics import collect_real_scorecard_metrics
from controlled_rollout.metrics_window import has_90_day_comparison
from controlled_rollout.rollout_policy import next_rollout_stage, rollback_sequence
from controlled_rollout.rollout_state_store import RolloutStateStore
from controlled_rollout.runbook_validator import validate_runbook
from controlled_rollout.scorecard import evaluate_golden_set
from productize.hotel_content_engine import run_hotel_content_engine

app = typer.Typer(help="Phase 8 controlled rollout + productize CLI (Growth Agent v3.1)")


@app.command("scorecard")
def scorecard_cmd(
    version: str = typer.Option(..., "--version", help='Golden set version tag, e.g. "growth-pilot-2026-08"'),
    project: str = typer.Option("venho_hotel"),
    data_root: Path = typer.Option(Path("data/projects")),
) -> None:
    """Build and evaluate a scorecard from real, already-persisted pilot
    data (not a fixture). Honestly reports missing dimensions as gate
    failures + `data_gaps` rather than fabricating numbers -- see
    `collect_real_scorecard_metrics`'s docstring."""
    golden_set = collect_real_scorecard_metrics(project=project, data_root=data_root, version=version)
    result = evaluate_golden_set(golden_set)
    typer.echo(
        json.dumps(
            {
                "version": result.version,
                "score": result.score,
                "passed": result.passed,
                "failures": result.failures,
                "sample_size": golden_set["sample_size"],
                "data_gaps": golden_set["data_gaps"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


@app.command("rollout-status")
def rollout_status_cmd(project: str = typer.Option("venho_hotel"), data_root: Path = typer.Option(Path("data/projects"))) -> None:
    typer.echo(json.dumps(RolloutStateStore(project, data_root).status(), ensure_ascii=False, indent=2))


@app.command("rollout-advance")
def rollout_advance_cmd(
    scorecard_version: str = typer.Option(..., "--scorecard-version"),
    metrics_days: int = typer.Option(
        0, "--metrics-days", help="Real days of baseline+candidate metric coverage on hand (0 if unknown/not tracked yet)."
    ),
    lane: str = typer.Option("standard", "--lane"),
    project: str = typer.Option("venho_hotel"),
    data_root: Path = typer.Option(Path("data/projects")),
) -> None:
    """Attempt to advance the real rollout stage. Always runs a real
    scorecard first -- there is no path to advance on an unverified claim
    of quality. `--metrics-days` is supplied by the caller today because no
    store yet tracks a real baseline-vs-candidate metrics window end to end
    (see `docs/growth/eval_golden_sets.md` gap); defaults to 0, which
    correctly blocks any stage requiring 90-day comparison."""
    golden_set = collect_real_scorecard_metrics(project=project, data_root=data_root, version=scorecard_version)
    scorecard = evaluate_golden_set(golden_set)
    has_90_day = metrics_days >= 90
    store = RolloutStateStore(project, data_root)
    current_stage = store.status()["current_stage"]
    decision = next_rollout_stage(current_stage, scorecard_passed=scorecard.passed, has_90_day_metrics=has_90_day, lane=lane)
    state = store.record_decision(
        {
            "current_stage": decision.current_stage,
            "next_stage": decision.next_stage,
            "allowed": decision.allowed,
            "reason": decision.reason,
            "human_approval_required": decision.human_approval_required,
            "scorecard_score": scorecard.score,
            "scorecard_passed": scorecard.passed,
        }
    )
    typer.echo(json.dumps({"decision": decision.__dict__, "scorecard": scorecard.__dict__, "state": state}, ensure_ascii=False, indent=2))
    if not decision.allowed:
        raise typer.Exit(code=1)


@app.command("rollback-plan")
def rollback_plan_cmd(disable_dispatch_done: bool = typer.Option(..., "--disable-dispatch-done")) -> None:
    typer.echo(json.dumps(rollback_sequence(disable_dispatch_done=disable_dispatch_done), ensure_ascii=False, indent=2))


@app.command("runbook-validate")
def runbook_validate_cmd(path: Path = typer.Option(Path("docs/growth/controlled_rollout_runbook.md"), "--path")) -> None:
    result = validate_runbook(path)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["valid"]:
        raise typer.Exit(code=1)


@app.command("productize-run")
def productize_run_cmd(
    project: str = typer.Option(..., "--project", help="A second hotel's config project id, e.g. hotel_2"),
    brief_json: Path = typer.Option(..., "--brief-json"),
    config_root: Path = typer.Option(Path("config/projects"), "--config-root"),
) -> None:
    """Run the `hotel-content-engine` productized skill for a second hotel
    (DoD #26: "Skill _productize chạy được cho hotel #2 không sửa core")
    from a JSON brief file, config-only -- no core module edits."""
    brief = json.loads(brief_json.read_text(encoding="utf-8"))
    result = run_hotel_content_engine(project=project, brief=brief, config_root=config_root)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))
