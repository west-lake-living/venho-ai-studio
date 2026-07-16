from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv

load_dotenv()

app = typer.Typer(
    name="venho",
    help="VENHO AI Studio — Knowledge-first AI production system",
    add_completion=False,
)

vision_app = typer.Typer(help="Knowledge Studio — AI Vision pipeline")
app.add_typer(vision_app, name="vision")

vault_app = typer.Typer(help="Knowledge Vault — search, diff, export DNA")
app.add_typer(vault_app, name="vault")

from validator_studio.cli import app as validator_app

app.add_typer(validator_app, name="validate")

from prompt_studio.cli import app as prompt_app

app.add_typer(prompt_app, name="prompt")

from automation_studio.cli import app as automation_app

app.add_typer(automation_app, name="auto")


def _confirm_one_subject_or_exit(subject: str, assume_one_subject: bool = False) -> None:
    """Require explicit one-tier confirmation before Mode B builds DNA."""
    typer.secho(
        f"  [v2.4 §2.1] Subject: '{subject}' — all images must be the SAME tier/subject.",
        fg=typer.colors.YELLOW,
    )
    if assume_one_subject:
        return
    confirmed = typer.confirm("Confirm this folder contains only one tier/subject", default=False)
    if not confirmed:
        typer.secho("Aborted. Split the folder by tier/subject and retry.", fg=typer.colors.RED)
        raise typer.Exit(1)


@vision_app.callback(invoke_without_command=True)
def vision_interactive(ctx: typer.Context) -> None:
    """Interactive entry point: if no subcommand given, show A/B menu."""
    if ctx.invoked_subcommand is None:
        typer.echo("\nVENHO AI Studio — Knowledge Studio\n")
        typer.echo("  [A] Describe any image as .md observation")
        typer.echo("  [B] Build DNA from multiple images of the same subject\n")
        choice = typer.prompt("Choose (A/B)").strip().upper()
        if choice == "A":
            _run_mode_a_interactive()
        elif choice == "B":
            _run_mode_b_interactive()
        else:
            typer.secho("Invalid choice. Run with --mode a or --mode b.", fg=typer.colors.RED)
            raise typer.Exit(1)


def _run_mode_a_interactive() -> None:
    from knowledge_studio.vision.pipeline import run_mode_a
    input_dir = Path(typer.prompt("Image folder path"))
    output_dir_str = typer.prompt("Output folder (leave blank for default)", default="")
    output_dir = Path(output_dir_str) if output_dir_str else None
    try:
        run_mode_a(input_dir=input_dir, output_dir=output_dir)
        typer.secho("Done!", fg=typer.colors.GREEN, bold=True)
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


def _run_mode_b_interactive() -> None:
    from knowledge_studio.vision.pipeline import run_mode_b
    project = typer.prompt("Project name", default="venho_hotel")
    subject = typer.prompt("Subject (room, lobby, facade, westlake, linh_an)")
    input_dir = Path(typer.prompt("Image folder path"))
    dna_version = typer.prompt("DNA version", default="1.0")
    # §2.1 — one subject = one tier confirmation
    typer.secho(
        "\n⚠  IMPORTANT (v2.4 §2.1): DNA quality requires that ALL images in the folder\n"
        "   belong to EXACTLY ONE tier/subject (e.g. all lake-view rooms, not mixed).",
        fg=typer.colors.YELLOW,
    )
    confirmed = typer.confirm("Does this folder contain ONLY ONE tier/subject?", default=True)
    if not confirmed:
        typer.secho("Aborted. Split the folder by tier/subject and retry.", fg=typer.colors.RED)
        raise typer.Exit(1)
    try:
        paths = run_mode_b(project=project, subject=subject, input_dir=input_dir, dna_version=dna_version)
        typer.secho("Done!", fg=typer.colors.GREEN, bold=True)
        typer.echo(f"  Markdown : {paths['md']}")
        typer.echo(f"  JSON     : {paths['json']}")
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@vision_app.command("observe")
def observe_cmd(
    mode: Optional[str] = typer.Option(None, "--mode", "-m", help="Pipeline mode: a (observe) or b (DNA builder)"),
    input_dir: Optional[Path] = typer.Option(None, "--input", "-i", help="Folder with images"),
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o", help="Output folder (Mode A only)"),
    project: str = typer.Option("venho_hotel", "--project", "-p", help="Project name (Mode B / --all)"),
    subject: Optional[str] = typer.Option(None, "--subject", "-s", help="Subject type (Mode B)"),
    outfit_id: Optional[str] = typer.Option(None, "--outfit-id", help="Stable wardrobe variant ID (Mode C)"),
    schema_subject: Optional[str] = typer.Option(None, "--schema-subject", help="Canonical schema subject (Mode C)"),
    display_label: Optional[str] = typer.Option(None, "--display-label", help="Friendly label for Mode C logs/UI"),
    dna_version: str = typer.Option("1.0", "--dna-version", help="DNA version label (Mode B / --all)"),
    provider: Optional[str] = typer.Option(None, "--provider", help="Override AI provider (openai/claude/mock)"),
    classify: bool = typer.Option(False, "--classify", help="Pass 0: classify mixed folder into subject groups"),
    classify_review: Optional[Path] = typer.Option(None, "--classify-review", help="Review YAML path for --classify results"),
    all_subjects: bool = typer.Option(False, "--all", help="Run Mode B for ALL subject folders under data/projects/<project>/media/"),
    assume_one_subject: bool = typer.Option(False, "--confirm-one-subject", help="Confirm Mode B input contains only one tier/subject"),
) -> None:
    """Run AI Vision pipeline in Mode A (observe), Mode B (DNA builder), --classify, or --all."""
    # --classify: run Pass 0 classification, print groups, then suggest Mode B commands
    if classify:
        from knowledge_studio.vision.pass0_classify import classify_folder, write_classification_review
        from knowledge_studio.vision.pipeline import _load_config, _make_client
        if input_dir is None:
            typer.secho("--input is required for --classify", fg=typer.colors.RED, err=True)
            raise typer.Exit(1)
        if not input_dir.is_dir():
            typer.secho(f"Input dir not found: {input_dir}", fg=typer.colors.RED, err=True)
            raise typer.Exit(1)
        try:
            cfg = _load_config()
            client = _make_client(cfg, provider)
            groups = classify_folder(input_dir, client)
            if not groups:
                typer.secho("No images found.", fg=typer.colors.YELLOW)
                return
            typer.secho("\nPass 0 — Classification results:", fg=typer.colors.CYAN, bold=True)
            for subj, paths in sorted(groups.items()):
                typer.echo(f"  {subj:<12} {len(paths):>3} image(s)")
            review_path = classify_review or (input_dir / "_classification_review.yaml")
            write_classification_review(groups, review_path, input_dir=input_dir)
            typer.echo(f"\n  Review file: {review_path}")
            typer.secho("\nBefore Mode B:", fg=typer.colors.CYAN)
            typer.echo("  1. Review and correct the suggested groups.")
            typer.echo("  2. Move approved images into data/projects/<project>/media/<subject>/ folders.")
            typer.echo("  3. Run Mode B only on one confirmed subject folder at a time.")
            typer.secho("\nExample commands after review:", fg=typer.colors.CYAN)
            for subj in sorted(groups.keys()):
                if subj != "general":
                    typer.echo(
                        f"  venho vision observe --mode b --project {project}"
                        f" --subject {subj} --input data/projects/{project}/media/{subj}"
                    )
        except Exception as e:
            typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
            raise typer.Exit(1)
        return

    # --all: run Mode B for every subject folder under data/projects/<project>/media/
    if all_subjects:
        from knowledge_studio.vision.pipeline import run_all
        typer.secho(
            f"\nVENHO AI Studio — --all mode (project: {project})",
            fg=typer.colors.CYAN, bold=True,
        )
        try:
            results = run_all(project=project, dna_version=dna_version, provider=provider)
            typer.secho(f"\n✓ --all complete: {len(results)} subject(s) built", fg=typer.colors.GREEN, bold=True)
            for subj, paths in results.items():
                typer.echo(f"  {subj:<20} → {paths['md'].name}")
        except Exception as e:
            typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
            raise typer.Exit(1)
        return

    from knowledge_studio.vision.pipeline import run_mode_a, run_mode_b, run_mode_c

    if input_dir is None:
        typer.secho("--input is required (unless using --all or --classify)", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    resolved_mode = (mode or "b").lower().strip("- ")

    try:
        if resolved_mode == "a":
            run_mode_a(input_dir=input_dir, output_dir=output_dir, provider=provider)
            typer.secho("Mode A complete.", fg=typer.colors.GREEN, bold=True)

        elif resolved_mode == "b":
            if not subject:
                typer.secho("--subject is required for Mode B", fg=typer.colors.RED, err=True)
                raise typer.Exit(1)
            if not input_dir.is_dir() or not any(input_dir.iterdir()):
                typer.secho(f"Input dir empty or missing: {input_dir}", fg=typer.colors.RED, err=True)
                raise typer.Exit(1)
            _confirm_one_subject_or_exit(subject, assume_one_subject=assume_one_subject)
            paths = run_mode_b(
                project=project, subject=subject,
                input_dir=input_dir, dna_version=dna_version, provider=provider,
            )
            typer.secho("Mode B complete.", fg=typer.colors.GREEN, bold=True)
            typer.echo(f"  Markdown : {paths['md']}")
            typer.echo(f"  JSON     : {paths['json']}")

        elif resolved_mode == "c":
            if not outfit_id:
                typer.secho("--outfit-id is required for Mode C", fg=typer.colors.RED, err=True)
                raise typer.Exit(1)
            if not input_dir.is_dir() or not any(input_dir.iterdir()):
                typer.secho(f"Input dir empty or missing: {input_dir}", fg=typer.colors.RED, err=True)
                raise typer.Exit(1)
            _confirm_one_subject_or_exit(outfit_id, assume_one_subject=assume_one_subject)
            paths = run_mode_c(
                project=project,
                outfit_id=outfit_id,
                schema_subject=schema_subject,
                display_label=display_label,
                input_dir=input_dir,
                dna_version=dna_version,
                provider=provider,
            )
            typer.secho("Mode C complete.", fg=typer.colors.GREEN, bold=True)
            typer.echo(f"  Markdown : {paths['md']}")
            typer.echo(f"  JSON     : {paths['json']}")

        else:
            typer.secho(f"Unknown mode '{resolved_mode}'. Use --mode a, --mode b, or --mode c.", fg=typer.colors.RED, err=True)
            raise typer.Exit(1)

    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@vision_app.command("bootstrap")
def bootstrap_cmd(
    subject: str = typer.Option(..., "--subject", "-s", help="Subject name for the new schema"),
    input_dir: Path = typer.Option(..., "--input", "-i", help="Folder with sample images (3–5 recommended)"),
    project: str = typer.Option("venho_hotel", "--project", "-p", help="Project name"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output YAML path (default: config/projects/<project>/subjects/<subject>.yaml)"),
    display_name: str = typer.Option("", "--display-name", help="Human-readable name for the subject"),
    description: str = typer.Option("", "--description", help="Short description of the subject"),
    provider: Optional[str] = typer.Option(None, "--provider", help="AI provider (openai/claude/mock)"),
    max_sample: int = typer.Option(3, "--max-sample", help="Max images to sample (default: 3)"),
) -> None:
    """Schema Bootstrap: analyze sample images and generate a starter YAML schema.

    Review and edit the output before using it for DNA generation.
    """
    from knowledge_studio.vision.schema_bootstrap import bootstrap_from_dir
    from knowledge_studio.vision.pipeline import _load_config, _make_client

    if not input_dir.is_dir():
        typer.secho(f"Input dir not found: {input_dir}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    resolved_output = output
    if resolved_output is None:
        base = Path(__file__).parent.parent.parent
        resolved_output = base / "config" / "projects" / project / "subjects" / f"{subject}.yaml"

    try:
        cfg = _load_config()
        client = _make_client(cfg, provider)
        result_path = bootstrap_from_dir(
            image_dir=input_dir,
            client=client,
            subject_name=subject,
            output_path=resolved_output,
            display_name=display_name,
            description=description,
            max_sample=max_sample,
        )
        typer.secho("Bootstrap complete.", fg=typer.colors.GREEN, bold=True)
        typer.echo(f"  Schema : {result_path}")
        typer.secho(
            "\n  IMPORTANT: Review and edit the schema before using it for DNA generation.",
            fg=typer.colors.YELLOW,
        )
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# vault — search / diff / export
# ---------------------------------------------------------------------------

@vault_app.command("search")
def vault_search_cmd(
    query: str = typer.Argument(..., help="Search term"),
    project: str = typer.Option("venho_hotel", "--project", "-p"),
    subject: Optional[str] = typer.Option(None, "--subject", "-s", help="Limit to one subject"),
    compact: bool = typer.Option(False, "--compact", "-c", help="Search COMPACT files only"),
    context: int = typer.Option(2, "--context", "-C", help="Context lines around each hit"),
    max_hits: int = typer.Option(50, "--max", help="Max hits to return"),
) -> None:
    """Full-text search across DNA files in the knowledge vault."""
    from knowledge_studio.vision.vault_search import search, format_results
    try:
        hits = search(query, project=project, subject=subject,
                      compact=compact, context_lines=context, max_hits=max_hits)
        typer.echo(format_results(hits, query))
    except FileNotFoundError as e:
        typer.secho(str(e), fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@vault_app.command("diff")
def vault_diff_cmd(
    subject: str = typer.Argument(..., help="Subject name (e.g. lake_view_room)"),
    project: str = typer.Option("venho_hotel", "--project", "-p"),
    version: Optional[str] = typer.Option(None, "--version", "-v",
                                           help="Archived version to compare from (e.g. 1.0). Default: latest archive."),
    list_versions: bool = typer.Option(False, "--list", "-l", help="List archived versions only, no diff"),
    context: int = typer.Option(3, "--context", "-C", help="Context lines in diff output"),
) -> None:
    """Compare an archived DNA version with the current version."""
    from knowledge_studio.vision.vault_diff import diff_versions, format_version_list
    if list_versions:
        typer.echo(format_version_list(project, subject))
        return
    try:
        result = diff_versions(project, subject, from_version=version, context=context)
        if result.startswith("No diff") or result.startswith("No archived"):
            typer.secho(result, fg=typer.colors.YELLOW)
        else:
            typer.echo(result)
    except FileNotFoundError as e:
        typer.secho(str(e), fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@vault_app.command("export")
def vault_export_cmd(
    subject: Optional[str] = typer.Argument(None, help="Subject name (omit for all subjects)"),
    project: str = typer.Option("venho_hotel", "--project", "-p"),
    full: bool = typer.Option(False, "--full", help="Export full DNA instead of COMPACT"),
    copy: bool = typer.Option(False, "--copy", help="Copy output to clipboard"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save to file instead of stdout"),
) -> None:
    """Export DNA as a GPT-ready text block (stdout, clipboard, or file)."""
    from knowledge_studio.vision.vault_export import export_subject, export_all, copy_to_clipboard
    compact = not full
    try:
        if subject:
            text = export_subject(project, subject, compact=compact)
        else:
            text = export_all(project, compact=compact)
    except FileNotFoundError as e:
        typer.secho(str(e), fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    if output:
        output.write_text(text, encoding="utf-8")
        typer.secho(f"Exported to: {output}", fg=typer.colors.GREEN)
    elif copy:
        ok = copy_to_clipboard(text)
        if ok:
            typer.secho("Copied to clipboard.", fg=typer.colors.GREEN)
        else:
            typer.secho("Clipboard copy failed. Printing to stdout instead.", fg=typer.colors.YELLOW)
            typer.echo(text)
    else:
        typer.echo(text)


# --- Legacy command (backward compat) ---
@vision_app.command("analyze")
def analyze(
    subject: str = typer.Option(..., "--subject", "-s"),
    input_dir: Path = typer.Option(..., "--input", "-i"),
    dna_version: str = typer.Option("1.0", "--dna-version"),
    project: str = typer.Option("venho_hotel", "--project", "-p"),
) -> None:
    """[Legacy] Run Mode B DNA pipeline. Prefer 'venho vision observe --mode b'."""
    from knowledge_studio.vision.pipeline import run_mode_b
    try:
        paths = run_mode_b(project=project, subject=subject, input_dir=input_dir, dna_version=dna_version)
        typer.secho("Done!", fg=typer.colors.GREEN, bold=True)
        typer.echo(f"  Markdown : {paths['md']}")
        typer.echo(f"  JSON     : {paths['json']}")
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
