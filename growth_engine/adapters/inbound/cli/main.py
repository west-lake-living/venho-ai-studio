from __future__ import annotations

from importlib import import_module
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
        from growth_engine.bootstrap import build_container

        service = build_container(settings).migration_service
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
        from growth_engine.bootstrap import build_container

        service = build_container(Settings.from_env()).legacy_import_service
    typer.echo(service.run(source, report))


@app.command()
def doctor(
    pre_switch: bool = typer.Option(False, "--pre-switch", help="Run checks before switching a release."),
) -> None:
    from growth_engine.bootstrap import build_container

    try:
        container = build_container(Settings.from_env())
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    report = container.doctor_service.run(pre_switch=pre_switch)
    typer.echo(report.render())
    if report.failed:
        raise typer.Exit(code=1)


@app.command()
def api(
    host: str = typer.Option("127.0.0.1", "--host", help="API bind address."),
    port: int = typer.Option(8021, "--port", min=1, max=65535, help="API bind port."),
) -> None:
    from growth_engine.adapters.inbound.api.app import create_app
    from growth_engine.bootstrap import build_container

    try:
        container = build_container(Settings.from_env())
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    try:
        uvicorn = import_module("uvicorn")
    except ImportError as error:
        typer.echo("Install the [api] extra to run the API command.", err=True)
        raise typer.Exit(code=1) from error
    uvicorn.run(create_app(container), host=host, port=port)
