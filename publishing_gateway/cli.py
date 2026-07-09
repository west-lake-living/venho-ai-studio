from __future__ import annotations

import json
from pathlib import Path

import typer

from publishing_gateway.gateway_router import publish_request
from publishing_gateway.receipt_store import ReceiptStore
from publishing_gateway.renderers import render_receipt_json, render_receipt_markdown
from publishing_gateway.schemas.delivery_receipt import DeliveryReceipt
from publishing_gateway.schemas.publishing_request import PublishingRequest

app = typer.Typer(help="Publishing Gateway dry-run publisher")


@app.command("publish")
def publish(
    package_file: Path = typer.Option(..., "--package-file"),
    approval_secret: str = typer.Option("test-secret", "--approval-secret"),
    dry_run: bool = typer.Option(True, "--dry-run/--live"),
    data_root: Path = typer.Option(Path("data/projects")),
    config_root: Path = typer.Option(Path("config/projects")),
) -> None:
    request = PublishingRequest.model_validate_json(package_file.read_text(encoding="utf-8"))
    receipt = publish_request(request, approval_secret=approval_secret, dry_run=dry_run, data_root=data_root, config_root=config_root)
    typer.echo(f"Receipt: {receipt.package_id}")
    typer.echo(f"Status: {receipt.overall_status}")
    typer.echo(render_receipt_json(receipt))


@app.command("retry")
def retry(
    package_file: Path = typer.Option(..., "--package-file"),
    platform: str = typer.Option(..., "--platform"),
    approval_secret: str = typer.Option("test-secret", "--approval-secret"),
    dry_run: bool = typer.Option(True, "--dry-run/--live"),
    data_root: Path = typer.Option(Path("data/projects")),
    config_root: Path = typer.Option(Path("config/projects")),
) -> None:
    request = PublishingRequest.model_validate_json(package_file.read_text(encoding="utf-8"))
    retry_request = request.model_copy(update={"platforms": [platform]})
    receipt = publish_request(retry_request, approval_secret=approval_secret, dry_run=dry_run, data_root=data_root, config_root=config_root)
    typer.echo(f"Retry: {platform}")
    typer.echo(f"Status: {receipt.overall_status}")


@app.command("receipt")
def receipt(package_id: str = typer.Option(...), project: str = typer.Option("venho_hotel"), data_root: Path = typer.Option(Path("data/projects"))) -> None:
    stored = ReceiptStore(project, data_root=data_root).find_by_package_id(package_id)
    if not stored:
        raise typer.Exit(1)
    typer.echo(render_receipt_markdown(DeliveryReceipt.model_validate(json.loads(json.dumps(stored)))))


@app.command("queue")
def queue_status() -> None:
    typer.echo("Queue status: in-memory queue is empty outside a publish run")


@app.command("version")
def version() -> None:
    typer.echo("publishing_gateway contract 1.0")


if __name__ == "__main__":
    app()
