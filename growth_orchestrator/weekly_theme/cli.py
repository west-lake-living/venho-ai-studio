from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from growth_orchestrator.weekly_theme.planner import plan_week

app = typer.Typer(help="Ven Ho weekly theme planner")


def _load_list(path: Path | None) -> list:
    if path is None or not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, list) else payload.get("items", [])


@app.command("plan")
def plan_cmd(
    week: Optional[str] = typer.Option(None, "--week", help="ISO week, e.g. 2026-W37."),
    local_beat_file: Optional[Path] = typer.Option(None, "--local-beat-file"),
    seasonal_file: Optional[Path] = typer.Option(None, "--seasonal-file"),
    trend_file: Optional[Path] = typer.Option(None, "--trend-file"),
    evergreen_file: Optional[Path] = typer.Option(None, "--evergreen-file"),
    recent_posts_file: Optional[Path] = typer.Option(None, "--recent-posts-file"),
    output: Optional[Path] = typer.Option(None, "--output"),
) -> None:
    """Create a plan from already collected local JSON inputs; no API calls."""
    plan = plan_week(
        week,
        local_beats=_load_list(local_beat_file),
        seasonal=_load_list(seasonal_file),
        trends=_load_list(trend_file),
        evergreen=_load_list(evergreen_file),
        recent_posts=_load_list(recent_posts_file),
    )
    payload = json.dumps(plan.to_dict(), ensure_ascii=False, indent=2)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload + "\n", encoding="utf-8")
    typer.echo(payload)


@app.command("types")
def types_cmd() -> None:
    """Print the six configured angle types."""
    from growth_orchestrator.weekly_theme.planner import load_angle_types

    typer.echo(json.dumps(load_angle_types(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    app()
