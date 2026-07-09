from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from content_studio.campaign_generator import generate_campaign
from content_studio.content_calendar import build_calendar
from content_studio.content_engine import generate_content
from content_studio.schemas.content_request import ContentRequest, SourceKnowledgeRef

app = typer.Typer(help="Content Studio draft generator")


@app.command("generate")
def generate(
    project: str = typer.Option("venho_hotel"),
    content_type: str = typer.Option("facebook_post", "--type"),
    topic: str = typer.Option(...),
    lang: str = typer.Option("vi", "--lang"),
    subject: str = typer.Option("westlake"),
    audience: str = typer.Option("Vietnamese leisure guests"),
    pillar: str = typer.Option("Khám phá Hồ Tây"),
    tone: str = typer.Option("warm, clear, trustworthy"),
    cta_type: str = typer.Option("booking_soft"),
    source_file: Optional[Path] = typer.Option(None),
) -> None:
    source_name = source_file.name if source_file else f"VENHO_HOTEL_{subject.upper()}_DNA.json"
    request = ContentRequest(
        project=project,
        content_type=content_type,
        topic=topic,
        target_audience=audience,
        content_pillar=pillar,
        tone=tone,
        target_language=lang,
        cta_type=cta_type,
        subject=subject,
        source_knowledge=[SourceKnowledgeRef(file=source_name, dna_version="1.0", hash="pending")],
    )
    result = generate_content(request)
    typer.echo(f"Markdown: {result.markdown_path}")
    typer.echo(f"JSON: {result.json_path}")
    typer.echo(f"Validation: {result.output.validation.status}")


@app.command("campaign")
def campaign(
    project: str = typer.Option("venho_hotel"),
    topic: str = typer.Option(...),
    channels: str = typer.Option("facebook,instagram,threads"),
    lang: str = typer.Option("vi", "--lang"),
    subject: str = typer.Option("westlake"),
    audience: str = typer.Option("Vietnamese leisure guests"),
    pillar: str = typer.Option("Khám phá Hồ Tây"),
    tone: str = typer.Option("warm, clear, trustworthy"),
) -> None:
    channel_list = [item.strip() for item in channels.split(",") if item.strip()]
    request = ContentRequest(
        project=project,
        content_type="facebook_post",
        topic=topic,
        target_audience=audience,
        content_pillar=pillar,
        tone=tone,
        target_language=lang,
        subject=subject,
        source_knowledge=[SourceKnowledgeRef(file=f"VENHO_HOTEL_{subject.upper()}_DNA.json", dna_version="1.0", hash="pending")],
    )
    result = generate_campaign(request, channel_list)
    typer.echo(f"Message core: {result.message_core}")
    for item in result.results:
        typer.echo(f"{item.output.content_type}: {item.markdown_path} ({item.output.validation.status})")


@app.command("calendar")
def calendar_cmd(
    project: str = typer.Option("venho_hotel"),
    month: str = typer.Option(...),
) -> None:
    result = build_calendar(project, month)
    typer.echo(f"Markdown: {result.markdown_path}")
    typer.echo(f"JSON: {result.json_path}")
    typer.echo(f"Entries: {len(result.entries)}")


if __name__ == "__main__":
    app()
