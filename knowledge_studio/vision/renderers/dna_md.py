from __future__ import annotations

from pathlib import Path

from knowledge_studio.vision.schemas.base import BaseDNA


def render_dna_md(dna: BaseDNA, project: str = "") -> str:
    """Render DNA to Markdown with fixed sections per §13 (v2.4)."""
    project_display = project or dna.project or "unknown"

    lines = [
        "# PROJECT SUBJECT DNA\n",
        "## META\n",
        f"- **project**: {project_display}",
        f"- **subject**: {dna.subject}",
        f"- **schema_id**: {dna.schema_id}",
        f"- **schema_version**: {dna.schema_version}",
        f"- **dna_version**: {dna.dna_version}",
        f"- **generated_at**: {dna.generated_at}",
        f"- **provider**: {dna.provider or 'unknown'}",
        f"- **model**: {dna.model or 'unknown'}",
        f"- **contract_version**: {dna.contract_version}",
        f"- **total_source_images**: {dna.evidence.total_images}",
        "",
    ]

    # INVARIANT
    lines.append("\n## INVARIANT\n")
    lines.append("*Features that are consistent and stable across all/most images.*\n")
    if dna.invariant:
        for feat in sorted(dna.invariant, key=lambda f: -f.coverage):
            cov_pct = f"{feat.coverage * 100:.0f}%"
            con_pct = f"{feat.consistency * 100:.0f}%"
            src_tag = f" `[{feat.value_source}]`" if feat.value_source == "curated" else ""
            lines.append(
                f"- **{feat.key}**: {feat.value}{src_tag}  "
                f"_(evidence: {feat.evidence_count}, coverage: {cov_pct}, consistency: {con_pct})_"
            )
    else:
        lines.append("*(none)*")

    # VARIABLE
    lines.append("\n\n## VARIABLE\n")
    lines.append("*Features that vary across images — all observed values listed.*\n")
    if dna.variable:
        for feat in dna.variable:
            values_str = " · ".join(f"`{v}`" for v in feat.value_range)
            lines.append(f"- **{feat.key}**: {values_str}")
    else:
        lines.append("*(none)*")

    # ALLOWED IMPERFECTIONS (v2.4 — Authenticity: trustworthy over beautiful)
    lines.append("\n\n## ALLOWED IMPERFECTIONS\n")
    lines.append("*Naturally occurring imperfections that are acceptable — and preferable for authenticity.*\n")
    if dna.allowed_imperfections:
        for ai in dna.allowed_imperfections:
            src_tag = f" `[{ai.source}]`"
            lines.append(f"- {ai.value}{src_tag}")
    else:
        lines.append("*(none)*")

    # FORBIDDEN — curated rules first, observed hints second, each tagged with source
    lines.append("\n\n## FORBIDDEN\n")
    lines.append("*Things NOT present — prevents AI hallucination. Curated rules are policy; observed rules are hints.*\n")
    if dna.forbidden:
        for rule in dna.forbidden:
            r = rule.rule if hasattr(rule, "rule") else str(rule)
            src = rule.source if hasattr(rule, "source") else "observed"
            lines.append(f"- {r} `[{src}]`")
    else:
        lines.append("*(none)*")

    # EVIDENCE
    lines.append("\n\n## EVIDENCE\n")
    lines.append(f"- **total_images**: {dna.evidence.total_images}")
    lines.append(f"- **invariant_count**: {len(dna.invariant)}")
    lines.append(f"- **variable_count**: {len(dna.variable)}")
    lines.append(f"- **source_hashes**: {', '.join(h[:8] for h in dna.source_images[:5])}" + (
        f"… (+{len(dna.source_images) - 5} more)" if len(dna.source_images) > 5 else ""
    ))

    # WEAK FEATURES
    lines.append("\n\n## WEAK FEATURES\n")
    lines.append("*Features seen in too few images to classify. Shoot more images.*\n")
    if dna.evidence.weak_features:
        for wf in dna.evidence.weak_features:
            lines.append(f"- **{wf.key}** (seen in {wf.evidence_count} image(s))")
    else:
        lines.append("*(none)*")

    # FUTURE CAPTURE NOTES
    lines.append("\n\n## FUTURE CAPTURE NOTES\n")
    if dna.future_capture_notes:
        for note in dna.future_capture_notes:
            lines.append(f"- {note}")
    else:
        lines.append("*(none)*")

    # CURATOR NOTES (v2.4 — from overlay)
    lines.append("\n\n## CURATOR NOTES\n")
    if dna.curator_notes:
        for note in dna.curator_notes:
            lines.append(f"- {note}")
    else:
        lines.append("*(none)*")

    lines.append("")
    return "\n".join(lines)


def write_dna_output(
    dna: BaseDNA,
    knowledge_dir: Path,
    dna_filename: str,
    project: str = "",
    write_compact: bool = False,
) -> dict[str, Path]:
    """Write DNA .md + .json (+ optional _COMPACT.md). Returns {md, json, compact?}."""
    from knowledge_studio.vision.renderers.dna_compact_md import render_dna_compact

    knowledge_dir.mkdir(parents=True, exist_ok=True)

    md_path = knowledge_dir / f"{dna_filename}.md"
    json_path = knowledge_dir / f"{dna_filename}.json"

    md_path.write_text(render_dna_md(dna, project), encoding="utf-8")
    json_path.write_text(dna.model_dump_json(indent=2), encoding="utf-8")

    result: dict[str, Path] = {"md": md_path, "json": json_path}

    if write_compact:
        compact_path = knowledge_dir / f"{dna_filename}_COMPACT.md"
        compact_path.write_text(render_dna_compact(dna, project), encoding="utf-8")
        result["compact"] = compact_path

    return result
