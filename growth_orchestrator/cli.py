from __future__ import annotations

import json
from pathlib import Path

import typer

from growth_orchestrator.application.run_content_pipeline import run_content_pipeline

app = typer.Typer(help="Ven Ho Growth Orchestrator")


@app.command("run")
def run(brief_file: Path) -> None:
    package = run_content_pipeline(json.loads(brief_file.read_text(encoding="utf-8")))
    typer.echo(json.dumps(package, ensure_ascii=False, indent=2))


@app.command("version")
def version() -> None:
    typer.echo("growth_orchestrator 0.1.0")


if __name__ == "__main__":
    app()
