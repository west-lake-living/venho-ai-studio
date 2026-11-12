from __future__ import annotations

import json
import os
import time
from datetime import date
from importlib import import_module
from pathlib import Path
from typing import Protocol

import typer

from growth_engine.settings import Settings


app = typer.Typer()
backup_cli = typer.Typer(help="Create an encrypted Growth Engine backup.")
app.add_typer(backup_cli, name="backup")


class MigrationService(Protocol):
    def run(self, db_path: Path, check: bool) -> str: ...


class LegacyImportService(Protocol):
    def run(self, source_dir: Path, report_path: Path) -> str: ...

    def apply(self, source_dir: Path, database_path: Path, report_path: Path) -> str: ...


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
    report: Path = typer.Option(..., "--report", help="Markdown import report output path."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Import only into a disposable database."),
    apply: bool = typer.Option(False, "--apply", help="Apply an approved delta to an existing migrated database."),
    target_database: Path | None = typer.Option(
        None,
        "--target-db",
        help="Existing, fully migrated SQLite target; required with --apply.",
    ),
) -> None:
    if dry_run == apply:
        raise typer.BadParameter("choose exactly one of --dry-run or --apply")
    if dry_run and target_database is not None:
        raise typer.BadParameter("--target-db is only valid with --apply")
    if apply and target_database is None:
        raise typer.BadParameter("--apply requires --target-db for an existing migrated SQLite database")
    service = ctx.obj.get("legacy_import_service") if isinstance(ctx.obj, dict) else None
    if service is None:
        from growth_engine.bootstrap import build_container

        service = build_container(Settings.from_env()).legacy_import_service
    try:
        if apply:
            typer.echo(service.apply(source, target_database, report))
        else:
            typer.echo(service.run(source, report))
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error


@app.command()
def openapi(
    out: Path = typer.Option(..., "--out", help="Write generated OpenAPI JSON to this path."),
) -> None:
    """Generate the API contract without opening DB or external services."""
    try:
        from types import SimpleNamespace

        from growth_engine.adapters.inbound.api.app import create_app
    except ImportError as error:
        typer.echo("Install the [api] extra to generate the OpenAPI contract.", err=True)
        raise typer.Exit(code=1) from error
    document = create_app(SimpleNamespace()).openapi()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    typer.echo(f"OpenAPI written: {out}")


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


@app.command()
def worker(
    lane: str = typer.Option(..., "--lane", help="Worker lane to run."),
) -> None:
    """Run the publish or content-jobs lane."""
    if lane not in {"publish", "jobs"}:
        raise typer.BadParameter("lane must be 'publish' or 'jobs'")
    settings = Settings.from_env()
    if not settings.db_path.strip() or "REQUIRED_FROM_P0" in settings.db_path:
        raise typer.BadParameter("configure GE_DB_PATH before running the worker")
    from growth_engine.bootstrap import build_container

    container = build_container(settings)
    worker_lane = container.publish_lane if lane == "publish" else container.jobs_lane
    raise typer.Exit(code=worker_lane.run_forever())


@app.command("prepare-slot")
def prepare_slot(
    local_date: str = typer.Option(..., "--date", help="Configured slot date in YYYY-MM-DD."),
    channel: str = typer.Option("fb_hanoi", "--channel", help="P4 production preparation currently supports fb_hanoi."),
) -> None:
    """Queue a single P4 content-only slot while production publishing is disabled and paused."""
    settings = Settings.from_env()
    from growth_engine.bootstrap import build_container

    try:
        parsed_date = date.fromisoformat(local_date)
        container = build_container(settings)
        result = container.queue_slot_generation.execute(parsed_date, channel_key=channel)
    except (ValueError, RuntimeError, OSError) as error:
        typer.echo(json.dumps({"result": "BLOCKED", "reason": type(error).__name__}), err=True)
        raise typer.Exit(code=1) from error
    typer.echo(json.dumps({
        "result": "QUEUED",
        "slot_id": result.slot_id,
        "job_id": result.job_id,
        "state": result.state,
        "replayed": result.replayed,
    }, ensure_ascii=False, sort_keys=True))


@app.command("cutover-readiness")
def cutover_readiness(
    local_date: str = typer.Option(..., "--date", help="Target slot date in YYYY-MM-DD."),
    local_time: str = typer.Option("09:00", "--time", help="Target slot time in Asia/Ho_Chi_Minh."),
) -> None:
    """Read-only gate: approved fb_hanoi delivery and production mapping dry run."""
    settings = Settings.from_env()
    from growth_engine.application.ops.cutover_readiness import CutoverReadiness

    try:
        date.fromisoformat(local_date)
        result = CutoverReadiness(settings.db_path).execute(local_date, local_time)
    except (ValueError, OSError) as error:
        typer.echo(json.dumps({"result": "FAIL", "reason": type(error).__name__}), err=True)
        raise typer.Exit(code=1) from error
    typer.echo(json.dumps({
        "result": "PASS" if result.ready else "FAIL",
        "slot": {"date": result.slot_date, "time": result.slot_time, "timezone": "Asia/Ho_Chi_Minh"},
        "delivery_id": result.delivery_id,
        "revision_id": result.revision_id,
        "mapping_dry_run": result.mapping_dry_run,
        "mapping_target_id": result.mapping_target_id,
        "mapping_route_ref": result.mapping_route_ref,
        "reasons": list(result.reasons),
    }, ensure_ascii=False, sort_keys=True))
    if not result.ready:
        raise typer.Exit(code=1)


@app.command("apply-test-receipts")
def apply_test_receipts() -> None:
    """Apply one batch of due receipts from the isolated TEST database only."""
    settings = Settings.from_env()
    if settings.env.casefold() != "test":
        raise typer.BadParameter("apply-test-receipts requires GE_ENV=test")
    test_state = (Path.home() / "venho/state/growth-engine-test").resolve()
    try:
        Path(settings.db_path).expanduser().resolve().relative_to(test_state)
    except ValueError as error:
        raise typer.BadParameter(
            "GE_DB_PATH must be inside the isolated TEST state directory"
        ) from error
    from growth_engine.bootstrap import build_container

    container = build_container(settings)
    result = container.process_receipt_jobs.execute()
    typer.echo(
        f"receipt_jobs claimed={result.claimed} completed={result.completed} failed={result.failed}"
    )
    if result.failed:
        raise typer.Exit(code=1)


@backup_cli.command("now")
def backup_now(
    ctx: typer.Context,
    destination: Path = typer.Option(..., "--destination", help="New .age backup artifact path."),
) -> None:
    """Snapshot SQLite and referenced media, then encrypt with age."""
    settings = Settings.from_env()
    if any("REQUIRED_FROM_P0" in value for value in (settings.db_path, settings.media_root)):
        raise typer.BadParameter("configure GE_DB_PATH and GE_MEDIA_ROOT before backup")
    recipient = os.environ.get("GE_AGE_RECIPIENT", "")
    try:
        container = _container(ctx, settings)
        result = container.backup_service.create(
            db_path=Path(settings.db_path),
            media_root=Path(settings.media_root),
            destination=destination,
            age_recipient=recipient,
            now_ms=time.time_ns() // 1_000_000,
        )
    except (ValueError, RuntimeError, OSError) as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(f"Backup created: {result.destination} ({result.artifact_count} media artifacts)")


@app.command()
def restore(
    ctx: typer.Context,
    from_backup: Path = typer.Option(..., "--from", help="Encrypted .age backup artifact."),
    target: Path = typer.Option(..., "--target", help="New empty restore target directory."),
    identity: Path = typer.Option(..., "--identity", help="Protected age identity file supplied by operator."),
) -> None:
    """Restore into a new directory with publishing disabled and epoch rotated."""
    try:
        settings = Settings.from_env()
        container = _container(ctx, settings)
        result = container.restore_service.restore(
            encrypted_backup=from_backup,
            target=target,
            identity_file=identity,
            now_ms=time.time_ns() // 1_000_000,
        )
    except (ValueError, RuntimeError, OSError) as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(
        f"Restored to {result.db_path}; publishing disabled; "
        f"rotated {result.dispatch_epochs_rotated} dispatch epoch(s)."
    )


def _container(ctx: typer.Context, settings: Settings):
    services = ctx.obj if isinstance(ctx.obj, dict) else {}
    container = services.get("container")
    if container is None:
        from growth_engine.bootstrap import build_container

        container = build_container(settings)
        services["container"] = container
        ctx.obj = services
    return container
