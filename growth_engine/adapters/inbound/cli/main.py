from __future__ import annotations

from pathlib import Path
from typing import Protocol

import typer

from growth_engine.settings import Settings


app = typer.Typer()


class MigrationService(Protocol):
    def run(self, db_path: Path, check: bool) -> str: ...


@app.callback()
def main(ctx: typer.Context) -> None:
    """Growth Engine command line."""
    if ctx.obj is None:
        ctx.obj = {}


@app.command()
def migrate(
    ctx: typer.Context,
    check: bool = typer.Option(False, "--check", help="Verify schema without applying migrations."),
) -> None:
    settings = Settings.from_env()
    configured_path = Path(settings.db_path)
    if "REQUIRED_FROM_P0" in str(configured_path) or not str(configured_path).strip():
        raise typer.BadParameter("configure GE_DB_PATH before running migrations")
    service = ctx.obj.get("migration_service") if isinstance(ctx.obj, dict) else None
    if service is None:
        typer.echo("Migration service is not wired into the CLI container yet.", err=True)
        raise typer.Exit(code=1)
    typer.echo(service.run(configured_path, check))
