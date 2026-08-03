from __future__ import annotations

import json
from pathlib import Path

import typer
import yaml

from research_engine.trend_radar.application.build_digest import build_digest
from research_engine.trend_radar.application.scan_trends import scan_trends

app = typer.Typer(help="Ven Ho Trend Radar")


@app.command("scan")
def scan(candidates_file: Path, config_root: Path = Path("config/projects/venho_hotel/research")) -> None:
    candidates = json.loads(candidates_file.read_text(encoding="utf-8"))
    trend_policy = yaml.safe_load((config_root / "trend_policy.yaml").read_text(encoding="utf-8"))
    safety_policy = yaml.safe_load((config_root / "brand_safety.yaml").read_text(encoding="utf-8"))
    typer.echo(json.dumps(scan_trends(candidates, trend_policy, safety_policy), ensure_ascii=False, indent=2))


@app.command("digest")
def digest(scored_file: Path) -> None:
    scored = json.loads(scored_file.read_text(encoding="utf-8"))
    typer.echo(json.dumps(build_digest(scored), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    app()
