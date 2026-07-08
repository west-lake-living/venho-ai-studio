"""DNA Compact Renderer — v2.4 §13.1.

Generates a stripped-down _COMPACT.md with only:
  INVARIANT (key + value)
  ALLOWED IMPERFECTIONS
  FORBIDDEN

Purpose: daily paste into Flow / ChatGPT to save context tokens.
Full DNA (.md + .json) is kept for storage and audit.
"""

from __future__ import annotations

from pathlib import Path

from knowledge_studio.vision.schemas.base import BaseDNA


def render_dna_compact(dna: BaseDNA, project: str = "") -> str:
    """Render compact DNA for daily AI production use."""
    subject_label = dna.subject.upper().replace("_", " ")

    lines = [
        f"# {subject_label} DNA — COMPACT\n",
        f"_project: {project or dna.project} · subject: {dna.subject} · v{dna.dna_version}_\n",
    ]

    # INVARIANT — key + value only (no evidence metadata)
    lines.append("\n## INVARIANT\n")
    lines.append("*Always present. Never deviate.*\n")
    if dna.invariant:
        for feat in sorted(dna.invariant, key=lambda f: -f.coverage):
            src_tag = " `[curated]`" if feat.value_source == "curated" else ""
            lines.append(f"- **{feat.key}**: {feat.value}{src_tag}")
    else:
        lines.append("*(none)*")

    # ALLOWED IMPERFECTIONS
    lines.append("\n\n## ALLOWED IMPERFECTIONS\n")
    lines.append("*Naturally occurring — acceptable and preferred for authenticity.*\n")
    if dna.allowed_imperfections:
        for ai in dna.allowed_imperfections:
            lines.append(f"- {ai.value}")
    else:
        lines.append("*(none)*")

    # FORBIDDEN
    lines.append("\n\n## FORBIDDEN\n")
    lines.append("*Do not generate. Policy from brand DNA.*\n")
    if dna.forbidden:
        for rule in dna.forbidden:
            r = rule.rule if hasattr(rule, "rule") else str(rule)
            lines.append(f"- {r}")
    else:
        lines.append("*(none)*")

    lines.append("")
    return "\n".join(lines)
