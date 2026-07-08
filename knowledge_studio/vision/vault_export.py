from __future__ import annotations

"""Vault export: package DNA for GPT consumption."""

from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).parent.parent.parent


def _knowledge_dir(project: str) -> Path:
    return BASE_DIR / "data" / "projects" / project / "knowledge"


def _dna_filename(project: str, subject: str) -> str:
    return f"{project.upper()}_{subject.upper()}_DNA"


def export_subject(
    project: str,
    subject: str,
    compact: bool = True,
) -> str:
    """Return DNA content for a subject, ready to paste into GPT.

    Uses COMPACT version by default (shorter, GPT-optimised).
    Falls back to full DNA if COMPACT not found.
    """
    knowledge_dir = _knowledge_dir(project)
    dna_filename = _dna_filename(project, subject)

    compact_path = knowledge_dir / f"{dna_filename}_COMPACT.md"
    full_path = knowledge_dir / f"{dna_filename}.md"

    if compact and compact_path.exists():
        chosen = compact_path
        label = "COMPACT"
    elif full_path.exists():
        chosen = full_path
        label = "FULL"
    else:
        raise FileNotFoundError(
            f"DNA not found for subject '{subject}'. Run Mode B first:\n"
            f"  venho vision observe --mode b --project {project} --subject {subject} --input <dir>"
        )

    content = chosen.read_text(encoding="utf-8")
    header = (
        f"# VENHO DNA Export — {subject.upper()} ({label})\n"
        f"# Project: {project} | File: {chosen.name}\n"
        f"# Paste this block into GPT as context before generating prompts.\n"
        "# ─────────────────────────────────────────────────────────────\n\n"
    )
    return header + content


def export_all(project: str, compact: bool = True) -> str:
    """Export all subjects in a project into one concatenated block."""
    knowledge_dir = _knowledge_dir(project)
    if not knowledge_dir.is_dir():
        raise FileNotFoundError(f"Knowledge directory not found: {knowledge_dir}")

    suffix = "_COMPACT.md" if compact else "_DNA.md"
    files = sorted(f for f in knowledge_dir.glob("*.md") if f.name.endswith(suffix))

    if not files:
        raise FileNotFoundError(
            f"No DNA files found in {knowledge_dir}. Run 'venho vision observe --all' first."
        )

    blocks = []
    for path in files:
        blocks.append(f"{'═' * 60}")
        blocks.append(f"# {path.stem}")
        blocks.append(f"{'═' * 60}")
        blocks.append(path.read_text(encoding="utf-8"))
        blocks.append("")

    header = (
        f"# VENHO DNA Export — ALL subjects ({project})\n"
        f"# {len(files)} DNA files | Paste this block into GPT as context.\n"
        f"# ─────────────────────────────────────────────────────────────\n\n"
    )
    return header + "\n".join(blocks)


def copy_to_clipboard(text: str) -> bool:
    """Copy text to macOS/Linux clipboard. Returns True on success."""
    import subprocess
    import platform

    try:
        if platform.system() == "Darwin":
            subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
        else:
            subprocess.run(["xclip", "-selection", "clipboard"],
                           input=text.encode("utf-8"), check=True)
        return True
    except Exception:
        return False
