from __future__ import annotations

from pathlib import Path

from knowledge_studio.vision.schemas.base import BaseObservation


# Map from observation category → §12 markdown section
_CATEGORY_TO_SECTION = {
    # Universal prompt categories
    "subject":      "SUBJECT",
    "subject_type": "SUBJECT",
    "scene_type":   "SUBJECT",
    "scene":        "SCENE",
    "environment":  "SCENE",
    "view":         "SCENE",
    "atmosphere":   "SCENE",
    "composition":  "COMPOSITION",
    "framing":      "COMPOSITION",
    "lighting":     "LIGHTING",
    "time_of_day":  "LIGHTING",
    "palette":      "PALETTE",
    "color":        "PALETTE",
    # Room-specific categories
    "structure":    "MATERIALS",
    "materials":    "MATERIALS",
    "furniture":    "AI-USABLE NOTES",
}


def _section(title: str, rows: list[tuple[str, str, float]]) -> str:
    if not rows:
        return f"\n## {title}\n\n*(no features)*\n"
    lines = [f"\n## {title}\n"]
    for key, value, conf in rows:
        if value and value != "not_visible":
            conf_str = f" _(conf: {conf:.2f})_" if conf < 0.8 else ""
            lines.append(f"- **{key}**: {value}{conf_str}")
    return "\n".join(lines) + "\n"


def render_single_md(obs: BaseObservation) -> str:
    """Render one observation to Markdown with fixed sections per §12."""
    SECTION_ORDER = ["SUBJECT", "SCENE", "COMPOSITION", "LIGHTING", "PALETTE", "MATERIALS", "AI-USABLE NOTES"]
    sections: dict[str, list[tuple[str, str, float]]] = {s: [] for s in SECTION_ORDER}
    seen: set[str] = set()

    for feat in obs.features:
        if feat.key in seen:
            continue
        seen.add(feat.key)
        if feat.value == "not_visible" or not feat.value:
            continue
        section = _CATEGORY_TO_SECTION.get(feat.category or "", "AI-USABLE NOTES")
        sections[section].append((feat.key, feat.value, feat.confidence))

    lines = [
        "# IMAGE OBSERVATION\n",
        "## META\n",
        f"- **image_file**: {obs.image_file}",
        f"- **image_hash**: {obs.image_hash[:12]}…",
        f"- **subject**: {obs.subject}",
        f"- **schema_id**: {obs.schema_id}",
        f"- **schema_version**: {obs.schema_version}",
        f"- **provider**: {obs.provider or 'unknown'}",
        f"- **model**: {obs.model or 'unknown'}",
        f"- **observed_at**: {obs.observed_at}",
        f"- **contract_version**: {obs.contract_version}",
        "",
    ]

    for section_name in SECTION_ORDER:
        lines.append(_section(section_name, sections[section_name]))

    if obs.notable_features:
        lines.append("\n## NOTABLE DETAILS\n")
        for note in obs.notable_features:
            lines.append(f"- {note}")
        lines.append("")

    if obs.uncertainty:
        lines.append("\n## UNCERTAINTY\n")
        for u in obs.uncertainty:
            lines.append(f"- {u}")
        lines.append("")
    else:
        lines.append("\n## UNCERTAINTY\n\n*(none noted)*\n")

    return "\n".join(lines)


def write_mode_a_output(
    obs: BaseObservation,
    output_dir: Path,
) -> dict[str, Path]:
    """Write observation .md + .json for Mode A. Returns {md, json}."""
    output_dir.mkdir(parents=True, exist_ok=True)

    stem = Path(obs.image_file).stem
    short_hash = obs.image_hash[:8]
    base_name = f"{stem}_{short_hash}"

    md_path = output_dir / f"{base_name}.md"
    json_path = output_dir / f"{base_name}.json"

    # Avoid name collision
    counter = 1
    while md_path.exists():
        md_path = output_dir / f"{base_name}_{counter}.md"
        json_path = output_dir / f"{base_name}_{counter}.json"
        counter += 1

    md_path.write_text(render_single_md(obs), encoding="utf-8")
    json_path.write_text(obs.model_dump_json(indent=2), encoding="utf-8")

    return {"md": md_path, "json": json_path}
