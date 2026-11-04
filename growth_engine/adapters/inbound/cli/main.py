from __future__ import annotations

from pathlib import Path
from typing import Protocol

import typer

from growth_engine.settings import Settings


app = typer.Typer()


class MigrationService(Protocol):
    def run(self, db_path: Path, check: bool) -> str: ...


class LegacyImportService(Protocol):
    def run(self, source_dir: Path, report_path: Path) -> str: ...


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


@app.command("legacy-import")
def legacy_import(
    ctx: typer.Context,
    source: Path = typer.Option(..., "--source", help="Directory containing read-only legacy snapshots."),
    report: Path = typer.Option(..., "--report", help="Markdown dry-run report output path."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Import only into a disposable database."),
) -> None:
    if not dry_run:
        raise typer.BadParameter("legacy-import supports only --dry-run; apply mode is not available")
    service = ctx.obj.get("legacy_import_service") if isinstance(ctx.obj, dict) else None
    if service is None:
        typer.echo("Legacy import service is not wired into the CLI container yet.", err=True)
        raise typer.Exit(code=1)
    typer.echo(service.run(source, report))
