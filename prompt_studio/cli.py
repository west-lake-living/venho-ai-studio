"""CLI for Prompt Studio (§15, §16 Step 14).

    venho prompt --type image   --project venho_hotel --subject lake_view_room --brief "..."
    venho prompt --type video   --project venho_hotel --subject linh_an,lake_view_room --brief "..."
    venho prompt --type content --project venho_hotel --subject westlake --lang vi --brief "..."
    venho prompt --type seo     --project venho_hotel --subject westlake --lang vi --brief "..." --keyword "..."
    venho prompt --all          --project venho_hotel --subject lake_view_room --brief "..."
    venho prompt                # interactive [A/B/C/D] menu

For video, `--subject` is a comma list: the FIRST entry is the character DNA, the rest are
environment DNA (§5.2). A single entry means environment-only (no character). `--all` runs
image + content + seo for one subject (not video, which needs an explicit multi-subject
combo). `--allow-draft` exports a DRAFT when Validate #2 still fails on the deterministic
prompt (§12).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Tuple

import typer

from prompt_studio.knowledge_reader import KnowledgeDna, read_dna
from prompt_studio.optimizer import optimize
from prompt_studio.pipeline import (
    FaithfulnessValidationFailed,
    OptimizeFn,
    PipelineResult,
    StructuralValidationFailed,
    run_content_pipeline,
    run_image_pipeline,
    run_seo_pipeline,
    run_video_pipeline,
)
from prompt_studio.prompt_store import DEFAULT_PROMPTS_ROOT

app = typer.Typer(
    help="Prompt Studio — turn merged DNA JSON into versioned production prompts", add_completion=False
)

PROMPT_TYPES = ("image", "video", "content", "seo")


def _resolve_dna_path(project: str, subject: str, knowledge_dir: Optional[Path] = None) -> Path:
    knowledge_dir = knowledge_dir or Path("data/projects") / project / "knowledge"
    candidates = sorted(knowledge_dir.glob(f"*_{subject.upper()}_DNA.json"))
    if not candidates:
        raise typer.BadParameter(f"No DNA JSON found for subject '{subject}' in {knowledge_dir}")
    return candidates[0]


def _read_dna(project: str, subject: str) -> KnowledgeDna:
    return read_dna(_resolve_dna_path(project, subject))


def _slugify(text: str, max_words: int = 5) -> str:
    words = re.findall(r"[A-Za-z0-9]+", text.lower())[:max_words]
    return "-".join(words) if words else "brief"


def _report(result: PipelineResult) -> None:
    typer.echo("")
    typer.secho(f"prompt_id: {result.contract.prompt_id}", bold=True)
    typer.echo(f"  type:       {result.contract.prompt_type}")
    typer.echo(f"  version:    {result.contract.prompt_version}")
    typer.echo(f"  decision:   {result.regeneration_decision or ('draft' if result.is_draft else '-')}")
    typer.echo(
        f"  validation: structural={result.contract.validation.structural}, "
        f"faithfulness={result.contract.validation.faithfulness}"
    )
    if result.used_optimizer:
        typer.echo(f"  optimizer:  {result.contract.optimizer.provider}/{result.contract.optimizer.model}")
    for note in result.notes:
        typer.secho(f"  note: {note}", fg=typer.colors.YELLOW)
    if result.paths:
        typer.echo(f"  saved:      {result.paths.markdown}")
    else:
        typer.echo("  saved:      (no change — Knowledge and template are unchanged)")


def _run_one(
    prompt_type: str,
    project: str,
    subject: Optional[str],
    brief: Optional[str],
    brief_slug: Optional[str],
    lang: Optional[str],
    keyword: Optional[str],
    allow_draft: bool,
    root: Path = DEFAULT_PROMPTS_ROOT,
    optimize_fn: OptimizeFn = optimize,
) -> PipelineResult:
    if prompt_type not in PROMPT_TYPES:
        typer.secho(f"Unknown --type '{prompt_type}' (must be one of {', '.join(PROMPT_TYPES)})", fg=typer.colors.RED)
        raise typer.Exit(1)
    if not subject or not brief:
        typer.secho("--subject and --brief are required", fg=typer.colors.RED)
        raise typer.Exit(1)

    slug = brief_slug or _slugify(brief)

    try:
        if prompt_type == "image":
            dna = _read_dna(project, subject)
            return run_image_pipeline(dna, brief, slug, allow_draft=allow_draft, root=root, optimize_fn=optimize_fn)

        if prompt_type == "video":
            subjects = [s.strip() for s in subject.split(",") if s.strip()]
            if len(subjects) == 1:
                character_dna, environment_dnas = None, [_read_dna(project, subjects[0])]
            else:
                character_dna = _read_dna(project, subjects[0])
                environment_dnas = [_read_dna(project, s) for s in subjects[1:]]
            return run_video_pipeline(
                environment_dnas, brief, slug, character_dna=character_dna, allow_draft=allow_draft, root=root,
                optimize_fn=optimize_fn,
            )

        if prompt_type == "content":
            dna = _read_dna(project, subject)
            return run_content_pipeline(
                dna, brief, slug, target_language=lang, allow_draft=allow_draft, root=root, optimize_fn=optimize_fn
            )

        dna = _read_dna(project, subject)  # seo
        return run_seo_pipeline(
            dna, brief, slug, keyword or brief, target_language=lang, allow_draft=allow_draft, root=root,
            optimize_fn=optimize_fn,
        )
    except (StructuralValidationFailed, FaithfulnessValidationFailed) as exc:
        typer.secho(f"Validation failed: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)


def _run_all(
    project: str,
    subject: Optional[str],
    brief: Optional[str],
    brief_slug: Optional[str],
    lang: Optional[str],
    keyword: Optional[str],
    allow_draft: bool,
    root: Path = DEFAULT_PROMPTS_ROOT,
    optimize_fn: OptimizeFn = optimize,
) -> None:
    if not subject or not brief:
        typer.secho("--subject and --brief are required with --all", fg=typer.colors.RED)
        raise typer.Exit(1)

    results: List[Tuple[str, Optional[PipelineResult], Optional[str]]] = []
    for prompt_type in ("image", "content", "seo"):  # video needs an explicit multi-subject combo
        try:
            result = _run_one(
                prompt_type, project, subject, brief, brief_slug, lang, keyword, allow_draft,
                root=root, optimize_fn=optimize_fn,
            )
            results.append((prompt_type, result, None))
        except typer.Exit as exc:
            results.append((prompt_type, None, f"exit code {exc.exit_code}"))

    typer.echo("\nRun report:")
    for prompt_type, result, error in results:
        if result is None:
            typer.secho(f"  [FAIL] {prompt_type}: {error}", fg=typer.colors.RED)
        else:
            status = result.regeneration_decision or ("draft" if result.is_draft else "-")
            typer.secho(f"  [OK]   {prompt_type}: {result.contract.prompt_id} ({status})", fg=typer.colors.GREEN)


def _run_interactive() -> None:
    typer.echo("\nVENHO AI Studio — Prompt Studio\n")
    typer.echo("  [A] Image")
    typer.echo("  [B] Video (multi-DNA)")
    typer.echo("  [C] Content")
    typer.echo("  [D] SEO\n")

    type_map = {"A": "image", "B": "video", "C": "content", "D": "seo"}
    choice = typer.prompt("Choose (A/B/C/D)").strip().upper()
    if choice not in type_map:
        typer.secho("Invalid choice.", fg=typer.colors.RED)
        raise typer.Exit(1)
    prompt_type = type_map[choice]

    project = typer.prompt("Project", default="venho_hotel")
    subject = typer.prompt(
        "Subject" if prompt_type != "video" else "Subject(s) — 'character,env1,env2' or just 'env' for no character"
    )
    brief = typer.prompt("Task brief")
    brief_slug = typer.prompt("Brief slug (short, for filename)", default=_slugify(brief))

    lang: Optional[str] = None
    if prompt_type in ("content", "seo"):
        lang = typer.prompt("Target language (vi/en/bilingual, blank = project default)", default="") or None

    keyword: Optional[str] = None
    if prompt_type == "seo":
        keyword = typer.prompt("Keyword intent", default=brief)

    allow_draft = typer.confirm("Allow DRAFT export if faithfulness validation fails?", default=False)

    result = _run_one(prompt_type, project, subject, brief, brief_slug, lang, keyword, allow_draft)
    _report(result)


@app.callback(invoke_without_command=True)
def prompt(
    ctx: typer.Context,
    type: Optional[str] = typer.Option(None, "--type", help="image | video | content | seo"),
    project: str = typer.Option("venho_hotel", "--project"),
    subject: Optional[str] = typer.Option(
        None, "--subject", help="Subject, or 'character,env1,env2' for video"
    ),
    brief: Optional[str] = typer.Option(None, "--brief", help="Task brief"),
    brief_slug: Optional[str] = typer.Option(
        None, "--brief-slug", help="Short slug for the filename; auto-derived from --brief if omitted"
    ),
    lang: Optional[str] = typer.Option(None, "--lang", help="vi | en | bilingual (content/seo)"),
    keyword: Optional[str] = typer.Option(
        None, "--keyword", help="SEO keyword intent (seo only; defaults to --brief)"
    ),
    all_types: bool = typer.Option(False, "--all", help="Generate image + content + seo for one subject"),
    allow_draft: bool = typer.Option(
        False, "--allow-draft", help="Export a DRAFT if faithfulness validation still fails"
    ),
) -> None:
    if ctx.invoked_subcommand is not None:
        return

    if all_types:
        _run_all(project, subject, brief, brief_slug, lang, keyword, allow_draft)
        return

    if type is None:
        _run_interactive()
        return

    result = _run_one(type, project, subject, brief, brief_slug, lang, keyword, allow_draft)
    _report(result)
