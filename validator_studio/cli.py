from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from validator_studio.validation_pipeline import (
    run_content_validation,
    run_face_validation,
    run_image_validation,
    run_latest_prompt_validation,
    run_prompt_validation,
)


app = typer.Typer(help="Validator Studio — deterministic output quality scoring")


@app.callback(invoke_without_command=True)
def validate_interactive(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is not None:
        return
    typer.echo("\nVENHO AI Studio — Validator Studio\n")
    typer.echo("  [A] Image validation")
    typer.echo("  [B] Prompt validation")
    typer.echo("  [C] Face validation (Phase 3)")
    typer.echo("  [D] Content validation (Phase 4)")
    choice = typer.prompt("Choose (A/B/C/D)").strip().upper()
    if choice == "A":
        project = typer.prompt("Project", default="venho_hotel")
        subject = typer.prompt("Subject", default="lake_view_room")
        image = Path(typer.prompt("Generated image path"))
        prompt = typer.prompt("Prompt JSON path (blank if none)", default="")
        _print_paths(run_image_validation(project, subject, image, Path(prompt) if prompt else None))
    elif choice == "B":
        project = typer.prompt("Project", default="venho_hotel")
        subject = typer.prompt("Subject", default="lake_view_room")
        prompt_file = Path(typer.prompt("Prompt JSON path"))
        _print_paths(run_prompt_validation(project, subject, prompt_file))
    elif choice == "C":
        project = typer.prompt("Project", default="venho_hotel")
        subject = typer.prompt("Subject", default="linh_an")
        image = Path(typer.prompt("Generated character image path"))
        _print_paths(run_face_validation(project, subject, image))
    elif choice == "D":
        project = typer.prompt("Project", default="venho_hotel")
        subject = typer.prompt("Subject", default="westlake")
        draft = Path(typer.prompt("Draft content path"))
        lang = typer.prompt("Target language (vi/en/bilingual, blank = project default)", default="") or None
        _print_paths(run_content_validation(project, subject, draft, target_language=lang))


@app.command("image")
def image_cmd(
    project: str = typer.Option("venho_hotel", "--project", "-p"),
    subject: str = typer.Option(..., "--subject", "-s"),
    image: Path = typer.Option(..., "--image", "-i"),
    prompt: Optional[Path] = typer.Option(None, "--prompt"),
    provider: str = typer.Option("mock", "--provider"),
    samples: Optional[int] = typer.Option(None, "--samples"),
    scenario_profile_id: Optional[str] = typer.Option(None, "--scenario-profile-id"),
) -> None:
    """Validate generated image artifact against DNA and optional prompt.json."""
    _print_paths(run_image_validation(project, subject, image, prompt, provider, samples, scenario_profile_id))


@app.command("prompt")
def prompt_cmd(
    project: str = typer.Option("venho_hotel", "--project", "-p"),
    subject: str = typer.Option(..., "--subject", "-s"),
    prompt_file: Optional[Path] = typer.Option(None, "--prompt-file"),
    latest: bool = typer.Option(False, "--latest", help="Resolve prompt JSON from Module 02 prompt_manifest.json"),
    type: Optional[str] = typer.Option(None, "--type", help="Required with --latest: image | video | content | seo"),
    brief_slug: Optional[str] = typer.Option(None, "--brief-slug", help="Optional manifest brief slug when more than one prompt exists"),
) -> None:
    """Validate prompt.json quality advisories against DNA."""
    if latest:
        if not type:
            typer.secho("--type is required with --latest", fg=typer.colors.RED)
            raise typer.Exit(1)
        _print_paths(run_latest_prompt_validation(project, subject, type, brief_slug))
        return
    if prompt_file is None:
        typer.secho("--prompt-file is required unless --latest is used", fg=typer.colors.RED)
        raise typer.Exit(1)
    _print_paths(run_prompt_validation(project, subject, prompt_file))


@app.command("face")
def face_cmd(
    project: str = typer.Option("venho_hotel", "--project", "-p"),
    subject: str = typer.Option(..., "--subject", "-s"),
    image: Path = typer.Option(..., "--image", "-i"),
    provider: str = typer.Option("mock", "--provider"),
    reference: Optional[list[Path]] = typer.Option(None, "--reference", help="Approved reference image(s) for direct comparison"),
    samples: int = typer.Option(1, "--samples", help="Vision-judge samples to average (majority-vote gates, mean scores)"),
) -> None:
    """Validate fictional character image against Face DNA and rubric 07F."""
    _print_paths(run_face_validation(project, subject, image, provider, reference, samples))


@app.command("content")
def content_cmd(
    project: str = typer.Option("venho_hotel", "--project", "-p"),
    subject: str = typer.Option(..., "--subject", "-s"),
    draft_file: Path = typer.Option(..., "--draft-file"),
    platform: str = typer.Option("facebook", "--platform"),
    lang: Optional[str] = typer.Option(None, "--lang"),
    prompt_file: Optional[Path] = typer.Option(None, "--prompt-file"),
) -> None:
    """Validate draft content against DNA, prompt rules, target language, and CTA policy."""
    _print_paths(run_content_validation(project, subject, draft_file, platform, lang, prompt_file))


def _print_paths(paths: dict[str, Path]) -> None:
    typer.secho("Validation complete.", fg=typer.colors.GREEN, bold=True)
    typer.echo(f"  Markdown : {paths['md']}")
    typer.echo(f"  JSON     : {paths['json']}")
