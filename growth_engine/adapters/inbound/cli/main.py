from __future__ import annotations

import json
import logging
import os
import re
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
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
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


@app.command("repair-p4-media")
def repair_p4_media(
    local_date: str = typer.Option(..., "--date", help="Existing P4 DRAFT slot date in YYYY-MM-DD."),
    channel: str = typer.Option("fb_hanoi", "--channel", help="P4 recovery is limited to fb_hanoi."),
    reference_asset_id: str | None = typer.Option(None, "--reference-asset-id", help="Catalog reference group matching the draft scene; prompted if omitted."),
) -> None:
    """Attach an allowlisted image to an existing DRAFT without regenerating its text package."""
    from growth_engine.bootstrap import build_container

    try:
        parsed_date = date.fromisoformat(local_date)
        container = build_container(Settings.from_env())
        allowed_references = sorted(container.repair_slot_media.allowed_reference_ids)
        if not allowed_references:
            raise ValueError(
                "no reviewed local image paths are configured in the image library"
            )
        preview = container.repair_slot_media.preview_context(
            parsed_date,
            channel_key=channel,
        )
        typer.echo(json.dumps({
            "draft_delivery_id": preview["delivery_id"],
            "topic_key": preview["topic_key"],
            "brief": preview["brief"],
            "available_reference_groups": allowed_references,
        }, ensure_ascii=False, sort_keys=True), err=True)
        chosen_reference = reference_asset_id or typer.prompt(
            "Legacy reference asset ID (" + ", ".join(allowed_references) + ")"
        )
        if chosen_reference not in allowed_references:
            raise ValueError("selected reference group is not in the reviewed image allowlist")
        result = container.repair_slot_media.execute(
            parsed_date,
            channel_key=channel,
            reference_asset_id=chosen_reference,
        )
    except (ValueError, RuntimeError, OSError) as error:
        typer.echo(json.dumps({
            "result": "BLOCKED",
            "reason": type(error).__name__,
            "message": _safe_cli_error(error),
        }, ensure_ascii=False, sort_keys=True), err=True)
        raise typer.Exit(code=1) from error
    typer.echo(json.dumps({
        "result": "QUEUED",
        "delivery_id": result.delivery_id,
        "asset_id": result.asset_id,
        "source_sha256": result.source_sha256,
        "source_relative_path": result.source_relative_path,
        "reference_asset_id": result.reference_asset_id,
        "prepare_job_id": result.prepare_job_id,
        "assemble_job_id": result.assemble_job_id,
        "requeued": result.requeued,
        "text_package_regenerated": False,
    }, ensure_ascii=False, sort_keys=True))


@app.command("resolve-p4-qc-unknown")
def resolve_p4_qc_unknown(
    ctx: typer.Context,
    job_id: str = typer.Option(..., "--job", help="UNKNOWN assemble_revision job ID for the 2026-11-21 P4 slot."),
    actual_minor: int | None = typer.Option(None, "--actual-minor", min=0, help="Settled legacy QC cost in VND minor units; defaults to the reserved per-call amount."),
    input_tokens: int | None = typer.Option(None, "--input-tokens", min=0, help="Provider usage evidence from the successful response."),
    output_tokens: int | None = typer.Option(None, "--output-tokens", min=0, help="Provider usage evidence from the successful response."),
) -> None:
    """Settle one evidenced P4 QC call and requeue exactly one controlled QC retry."""
    from growth_engine.application.ops.resolve_p4_qc_unknown import (
        P4QcResolutionError,
    )

    try:
        settings = Settings.from_env()
        if settings.env.lower() != "production":
            raise P4QcResolutionError("resolution command is restricted to production")
        service = ctx.obj.get("resolve_p4_qc_unknown_service") if isinstance(ctx.obj, dict) else None
        if service is None:
            from growth_engine.bootstrap import build_container

            service = build_container(settings).resolve_p4_qc_unknown
        preview = service.preview(job_id, actual_minor=actual_minor)
        if preview.already_resolved:
            typer.echo(json.dumps({
                "result": "ALREADY_RESOLVED",
                "job_id": preview.job_id,
                "delivery_id": preview.delivery_id,
                "paid_call_id": preview.paid_call_id,
                "actual_minor": preview.actual_minor,
            }, sort_keys=True))
            return
        if (input_tokens is None) != (output_tokens is None):
            raise P4QcResolutionError("supply both --input-tokens and --output-tokens, or neither")
        typer.echo(json.dumps({
            "preflight": "READY",
            "job_id": preview.job_id,
            "delivery_id": preview.delivery_id,
            "slot": {"date": preview.slot_date, "time": preview.slot_time, "timezone": "Asia/Ho_Chi_Minh"},
            "paid_call_id": preview.paid_call_id,
            "paid_call_state": preview.paid_call_state,
            "reserved_minor": preview.reserved_minor,
            "actual_minor": preview.actual_minor,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "publishing": "DISABLED + global_pause required",
        }, ensure_ascii=False, sort_keys=True))
        if typer.prompt("Gõ RESOLVE để settle chi phí và requeue một lần QC") != "RESOLVE":
            typer.echo("RESOLVE=DECLINED; no changes made")
            raise typer.Exit(code=2)
        result = service.execute(
            job_id,
            actual_minor=actual_minor,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
    except typer.Exit:
        raise
    except P4QcResolutionError as error:
        typer.echo(json.dumps({"result": "BLOCKED", "reason": str(error)}, ensure_ascii=False), err=True)
        raise typer.Exit(code=1) from error
    except (OSError, ValueError, RuntimeError) as error:
        typer.echo(json.dumps({"result": "BLOCKED", "reason": type(error).__name__}, ensure_ascii=False), err=True)
        raise typer.Exit(code=1) from error
    typer.echo(json.dumps({
        "result": "RESOLVED_AND_REQUEUED",
        "job_id": result.job_id,
        "delivery_id": result.delivery_id,
        "paid_call_id": result.paid_call_id,
        "actual_minor": result.actual_minor,
        "qc_retry_key": result.qc_retry_key,
        "already_resolved": result.already_resolved,
    }, ensure_ascii=False, sort_keys=True))


@app.command("p4-slot-status")
def p4_slot_status(
    local_date: str = typer.Option(..., "--date", help="P4 slot date in YYYY-MM-DD."),
) -> None:
    """Read-only P4 status summary; omits caption, file paths, Drive URLs and secrets."""
    import sqlite3

    try:
        settings = Settings.from_env()
        parsed_date = date.fromisoformat(local_date)
        db_path = Path(settings.db_path).expanduser().resolve()
        connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        try:
            controls = connection.execute(
                "SELECT publish_mode, global_pause FROM runtime_controls WHERE environment='production'"
            ).fetchone()
            target = connection.execute(
                """SELECT s.id AS slot_id, s.local_date, s.local_time,
                          d.id AS delivery_id, d.state AS delivery_state, d.current_revision_id,
                          d.row_version, d.package_id, p.created_at AS package_created_at,
                          p.source_snapshot_json, p.fact_snapshot_json,
                          c.enabled, c.remote_account_id
                   FROM slots s JOIN slot_targets st ON st.slot_id=s.id
                   JOIN channels c ON c.id=st.channel_id
                   LEFT JOIN deliveries d ON d.target_id=st.id AND d.active=1
                   LEFT JOIN content_packages p ON p.id=d.package_id
                   WHERE c.environment='production' AND c.channel_key='fb_hanoi'
                     AND s.local_date=? AND s.local_time='09:00'
                   ORDER BY s.id LIMIT 1""",
                (parsed_date.isoformat(),),
            ).fetchone()
            if target is None:
                raise ValueError("P4 fb_hanoi slot was not found")
            package_snapshot = json.loads(str(target["source_snapshot_json"] or "{}"))
            package_images = package_snapshot.get("images", [])
            if not isinstance(package_images, list):
                package_images = []
            asset_ids = {
                str(image["asset_id"])
                for image in package_images
                if isinstance(image, dict) and isinstance(image.get("asset_id"), str)
            }
            package_created_at = int(target["package_created_at"] or 0)
            delivery_id = target["delivery_id"]
            related_jobs: list[dict[str, object]] = []
            rows = connection.execute(
                """SELECT id,kind,state,attempts,last_error,payload_json,created_at
                   FROM jobs WHERE lane='jobs' AND kind IN ('generate_slot','prepare_variant','assemble_revision')
                     AND created_at>=? ORDER BY created_at,id""",
                (package_created_at,),
            ).fetchall()
            decoded_jobs: list[tuple[sqlite3.Row, dict[str, object]]] = []
            for job in rows:
                payload = json.loads(str(job["payload_json"]))
                decoded_jobs.append((job, payload))
                if payload.get("delivery_id") == delivery_id:
                    options = payload.get("asset_options", [])
                    if not isinstance(options, list):
                        options = []
                    for option in options:
                        if isinstance(option, dict) and isinstance(option.get("asset_id"), str):
                            asset_ids.add(str(option["asset_id"]))
            for job, payload in decoded_jobs:
                related = (
                    payload.get("slot_id") == target["slot_id"]
                    or payload.get("delivery_id") == delivery_id
                    or payload.get("asset_id") in asset_ids
                )
                if related:
                    related_jobs.append({
                        "id": str(job["id"]),
                        "kind": str(job["kind"]),
                        "state": str(job["state"]),
                        "attempts": int(job["attempts"]),
                        "last_error": None if not job["last_error"] else _safe_cli_error_text(str(job["last_error"])),
                    })
            if asset_ids:
                placeholders = ",".join("?" for _ in asset_ids)
                media_assets = int(connection.execute(
                    f"SELECT count(*) FROM media_assets WHERE id IN ({placeholders})", tuple(asset_ids)
                ).fetchone()[0])
                media_variants = int(connection.execute(
                    f"SELECT count(*) FROM media_variants WHERE asset_id IN ({placeholders})", tuple(asset_ids)
                ).fetchone()[0])
                qc_reports = int(connection.execute(
                    f"""SELECT count(*) FROM qc_reports q JOIN media_variants v ON v.id=q.variant_id
                        WHERE v.asset_id IN ({placeholders})""",
                    tuple(asset_ids),
                ).fetchone()[0])
            else:
                media_assets = media_variants = qc_reports = 0
            if delivery_id:
                outbox_count = int(connection.execute(
                    "SELECT count(*) FROM outbox_commands WHERE delivery_id=?", (delivery_id,)
                ).fetchone()[0])
                execution_count = int(connection.execute(
                    "SELECT count(*) FROM executions WHERE delivery_id=?", (delivery_id,)
                ).fetchone()[0])
            else:
                outbox_count = execution_count = 0
            revision = None
            paid_call_keys: list[str] = []
            paid_call_prefixes = [f"generate:{target['slot_id']}:%"]
            if target["current_revision_id"]:
                revision_row = connection.execute(
                    """SELECT r.id,r.payload_hash,v.sha256 AS variant_sha256,
                              v.mime,v.width,v.height,v.byte_size,v.qc_status,
                              q.decision AS qc_decision,q.caption_hash,q.ruleset_hash,
                              q.fact_snapshot_hash
                       FROM delivery_revisions r JOIN media_variants v ON v.id=r.variant_id
                       JOIN qc_reports q ON q.id=r.qc_report_id WHERE r.id=?""",
                    (target["current_revision_id"],),
                ).fetchone()
                if revision_row is not None:
                    revision = dict(revision_row)
                    paid_call_keys.append(
                        "qc:{variant_sha256}:{caption_hash}:{fact_snapshot_hash}:{ruleset_hash}".format(
                            **dict(revision_row)
                        )
                    )
            paid_call_where = ["business_key LIKE ?"]
            paid_call_params: list[str] = list(paid_call_prefixes)
            if asset_ids:
                placeholders = ",".join("?" for _ in asset_ids)
                variant_hashes = [str(row[0]) for row in connection.execute(
                    f"SELECT DISTINCT sha256 FROM media_variants WHERE asset_id IN ({placeholders})",
                    tuple(asset_ids),
                ).fetchall()]
                for variant_sha in variant_hashes:
                    paid_call_where.append("business_key LIKE ?")
                    paid_call_params.append(f"qc:{variant_sha}:%")
            for business_key in paid_call_keys:
                paid_call_where.append("business_key LIKE ?")
                paid_call_params.append(business_key + "%")
            paid_calls = [dict(row) for row in connection.execute(
                """SELECT operation,state,reserved_minor,actual_minor
                   FROM paid_calls WHERE """ + " OR ".join(paid_call_where) + " ORDER BY created_at,id",
                tuple(paid_call_params),
            ).fetchall()]
        finally:
            connection.close()
    except (OSError, sqlite3.Error, ValueError) as error:
        typer.echo(json.dumps({"result": "FAIL", "reason": type(error).__name__, "message": _safe_cli_error(error)}, sort_keys=True), err=True)
        raise typer.Exit(code=1) from error
    typer.echo(json.dumps({
        "result": "OK",
        "slot": {"date": str(target["local_date"]), "time": str(target["local_time"]), "timezone": "Asia/Ho_Chi_Minh"},
        "controls": None if controls is None else dict(controls),
        "channel": {"key": "fb_hanoi", "enabled": bool(target["enabled"]), "remote_account_id": str(target["remote_account_id"])},
        "delivery": None if not delivery_id else {
            "id": str(delivery_id),
            "state": str(target["delivery_state"]),
            "row_version": int(target["row_version"]),
            "revision_id": target["current_revision_id"],
            "package_id": str(target["package_id"]),
        },
        "revision": revision,
        "media": {"assets": media_assets, "variants": media_variants, "qc_reports": qc_reports},
        "jobs": related_jobs,
        "paid_calls": paid_calls,
        "outbox_count": outbox_count,
        "execution_count": execution_count,
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


_CLI_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(authorization|bearer|access[_-]?token|refresh[_-]?token|api[_-]?key|client[_-]?secret|password)"
    r"(\s*[:=]\s*|\s+)([^\s,;]+)"
)
_CLI_URL = re.compile(r"https?://[^\s\])}>,]+", re.IGNORECASE)
_CLI_LONG_SECRET = re.compile(r"\b[A-Za-z0-9_-]{48,}\b")
_CLI_KEY = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|EAA[A-Za-z0-9_-]{16,}|ya29\.[A-Za-z0-9._-]{16,})\b")


def _safe_cli_error(error: Exception) -> str:
    return _safe_cli_error_text(str(error) or type(error).__name__)


def _safe_cli_error_text(message: str) -> str:
    safe = _CLI_SECRET_ASSIGNMENT.sub(r"\1\2[REDACTED]", message)
    safe = _CLI_URL.sub("[URL REDACTED]", safe)
    safe = _CLI_KEY.sub("[SECRET REDACTED]", safe)
    safe = _CLI_LONG_SECRET.sub("[SECRET REDACTED]", safe)
    return " ".join(safe.split())[:384]
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
