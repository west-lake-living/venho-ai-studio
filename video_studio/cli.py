from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from prompt_studio.knowledge_reader import read_dna

from video_studio.schemas.video_request import SourceKnowledgeRef, VideoRequest
from video_studio.video_engine import generate_video_package

app = typer.Typer(help="Video Studio package generator")


def _source_ref(project: str, subject: str, data_root: Path) -> SourceKnowledgeRef:
    path = data_root / project / "knowledge" / f"VENHO_HOTEL_{subject.upper()}_DNA.json"
    dna = read_dna(path)
    return SourceKnowledgeRef(file=path.name, dna_version=dna.dna_version, hash=f"sha256:{dna.content_hash}")


@app.command("generate")
def generate(
    project: str = typer.Option("venho_hotel"),
    video_type: str = typer.Option("social_reel", "--type"),
    topic: str = typer.Option(...),
    duration: int = typer.Option(15, "--duration"),
    aspect_ratio: str = typer.Option("9:16"),
    platform: str = typer.Option("instagram_reels"),
    lang: str = typer.Option("vi", "--lang"),
    engine: str = typer.Option("veo"),
    subjects: str = typer.Option("lake_view_room,westlake"),
    include_character: bool = typer.Option(False),
    audience: str = typer.Option("Vietnamese leisure guests"),
    data_root: Path = typer.Option(Path("data/projects")),
    no_validate: bool = typer.Option(False),
) -> None:
    source_knowledge = [_source_ref(project, subject.strip(), data_root) for subject in subjects.split(",") if subject.strip()]
    request = VideoRequest(
        project=project,
        video_type=video_type,
        topic=topic,
        duration_seconds=duration,
        aspect_ratio=aspect_ratio,
        platform=platform,
        caption_language=lang,
        include_character=include_character,
        target_audience=audience,
        source_knowledge=source_knowledge,
        target_engine=engine,
        validation_required=not no_validate,
    )
    result = generate_video_package(request, data_root=data_root, validate=not no_validate)
    typer.echo(f"Markdown: {result.markdown_path}")
    typer.echo(f"JSON: {result.json_path}")
    typer.echo(f"Manifest: {result.manifest_path}")
    typer.echo(f"Validation: {result.package.validation.status}")


@app.command("version")
def version() -> None:
    typer.echo("video_studio contract 1.0")


if __name__ == "__main__":
    app()
