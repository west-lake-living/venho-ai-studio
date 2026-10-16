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

PAID_CALL_BLOCKED_EXIT_CODE = 3
PAID_CALL_BLOCKED_MARKER = "VALIDATOR_PAID_CALL_BLOCKED_BEFORE_TRANSPORT"
# Printed after the report paths. The name must not contain "JSON": faceless-video takes the first
# stdout line containing "JSON" and ":" as the report path.
USAGE_MARKER = "VALIDATOR_USAGE"


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
    output_root: Optional[Path] = typer.Option(None, "--output-root", help="Validation artifact root; default is the live project validation store"),
) -> None:
    """Validate generated image artifact against DNA and optional prompt.json."""
    from shared.vision.paid_call_guard import PaidCallBlocked

    try:
        paths = run_image_validation(
            project, subject, image, prompt, provider, samples, scenario_profile_id, output_root
        )
    except PaidCallBlocked as exc:
        # Same contract as `face`: refused before the SDK transport, so nothing was charged.
        typer.echo(f"{PAID_CALL_BLOCKED_MARKER}: {exc}", err=True)
        raise typer.Exit(PAID_CALL_BLOCKED_EXIT_CODE) from exc
    _print_paths(paths)
    _print_usage()


@app.command("clip")
def clip_cmd(
    sheet: list[Path] = typer.Option(..., "--sheet", help="Contact sheet PNG; repeat in time order"),
    brief: Path = typer.Option(..., "--brief", help="JSON: prompt, expected_people, duration_sec"),
    provider: str = typer.Option("gemini", "--provider"),
    output_root: Optional[Path] = typer.Option(None, "--output-root"),
) -> None:
    """Review a generated motion clip from contact sheets (clip-review-v1)."""
    import json as _json

    from shared.vision.paid_call_guard import PaidCallBlocked
    from validator_studio.clip_reviewer import review_clip, write_clip_review

    if provider != "gemini":
        raise typer.BadParameter("clip review supports only --provider gemini")
    try:
        report = review_clip(sheet, _json.loads(brief.read_text(encoding="utf-8")))
    except PaidCallBlocked as exc:
        typer.echo(f"{PAID_CALL_BLOCKED_MARKER}: {exc}", err=True)
        raise typer.Exit(PAID_CALL_BLOCKED_EXIT_CODE) from exc
    out_dir = (output_root or Path("data/projects/venho_hotel/validation")) / "clip_reviews"
    typer.echo(f"  JSON     : {write_clip_review(report, out_dir)}")
    _print_usage()


@app.command("prompt")
def prompt_cmd(
    project: str = typer.Option("venho_hotel", "--project", "-p"),
    subject: str = typer.Option(..., "--subject", "-s"),
    prompt_file: Optional[Path] = typer.Option(None, "--prompt-file"),
    latest: bool = typer.Option(False, "--latest", help="Resolve prompt JSON from Module 02 prompt_manifest.json"),
    type: Optional[str] = typer.Option(None, "--type", help="Required with --latest: image | video | content | seo"),
    brief_slug: Optional[str] = typer.Option(None, "--brief-slug", help="Optional manifest brief slug when more than one prompt exists"),
    output_root: Optional[Path] = typer.Option(None, "--output-root", help="Validation artifact root; default is the live project validation store"),
) -> None:
    """Validate prompt.json quality advisories against DNA."""
    if latest:
        if not type:
            typer.secho("--type is required with --latest", fg=typer.colors.RED)
            raise typer.Exit(1)
        _print_paths(run_latest_prompt_validation(project, subject, type, brief_slug, output_root))
        return
    if prompt_file is None:
        typer.secho("--prompt-file is required unless --latest is used", fg=typer.colors.RED)
        raise typer.Exit(1)
    _print_paths(run_prompt_validation(project, subject, prompt_file, output_root))


@app.command("face")
def face_cmd(
    project: str = typer.Option("venho_hotel", "--project", "-p"),
    subject: str = typer.Option(..., "--subject", "-s"),
    image: Path = typer.Option(..., "--image", "-i"),
    provider: str = typer.Option("mock", "--provider"),
    reference: Optional[list[Path]] = typer.Option(None, "--reference", help="Approved reference image(s) for direct comparison"),
    samples: int = typer.Option(1, "--samples", help="Vision-judge samples to average (majority-vote gates, mean scores)"),
    output_root: Optional[Path] = typer.Option(None, "--output-root", help="Validation artifact root; default is the live project validation store"),
) -> None:
    """Validate fictional character image against Face DNA and rubric 07F."""
    from shared.vision.paid_call_guard import PaidCallBlocked

    try:
        paths = run_face_validation(project, subject, image, provider, reference, samples, output_root)
    except PaidCallBlocked as exc:
        # The guard raises before the SDK transport, so no request left this process. Callers
        # (faceless-video) rely on this exit code + marker to prove no charge was incurred.
        typer.echo(f"{PAID_CALL_BLOCKED_MARKER}: {exc}", err=True)
        raise typer.Exit(PAID_CALL_BLOCKED_EXIT_CODE) from exc
    _print_paths(paths)
    _print_usage()


@app.command("content")
def content_cmd(
    project: str = typer.Option("venho_hotel", "--project", "-p"),
    subject: str = typer.Option(..., "--subject", "-s"),
    draft_file: Path = typer.Option(..., "--draft-file"),
    platform: str = typer.Option("facebook", "--platform"),
    lang: Optional[str] = typer.Option(None, "--lang"),
    prompt_file: Optional[Path] = typer.Option(None, "--prompt-file"),
    output_root: Optional[Path] = typer.Option(None, "--output-root", help="Validation artifact root; default is the live project validation store"),
) -> None:
    """Validate draft content against DNA, prompt rules, target language, and CTA policy."""
    _print_paths(run_content_validation(project, subject, draft_file, platform, lang, prompt_file, output_root))


@app.command("health")
def health_cmd(
    project: str = typer.Option("venho_hotel", "--project", "-p"),
    subject: str = typer.Option("linh_an", "--subject", "-s"),
    expected_model: str = typer.Option(..., "--expected-model", help="Pinned Gemini model the caller authorized"),
    max_text_bytes: Optional[int] = typer.Option(None, "--max-text-bytes", help="Caller's priced bound on prompt+schema+user text"),
) -> None:
    """Non-media readiness of the live face validator. Never calls Gemini, never costs money."""
    import json

    from validator_studio.health import validator_health

    result = validator_health(project, subject, expected_model, max_text_bytes)
    typer.echo(json.dumps(result, sort_keys=True, separators=(",", ":")))
    if result["status"] != "READY":
        raise typer.Exit(2)


def _print_usage() -> None:
    import json

    from shared.vision.paid_call_guard import usage_summary

    typer.echo(f"{USAGE_MARKER} {json.dumps(usage_summary(), sort_keys=True)}")


def _print_paths(paths: dict[str, Path]) -> None:
    typer.secho("Validation complete.", fg=typer.colors.GREEN, bold=True)
    typer.echo(f"  Markdown : {paths['md']}")
    typer.echo(f"  JSON     : {paths['json']}")
