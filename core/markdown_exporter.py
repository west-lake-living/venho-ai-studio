import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from core.logger import log

BASE_DIR = Path(__file__).parent.parent


def _confidence_badge(level: str) -> str:
    badges = {"HIGH": "🟢 HIGH", "MEDIUM": "🟡 MEDIUM", "LOW": "🔴 LOW"}
    return badges.get(level, level)


def export(dna: dict, meta: dict, output_name: Optional[str] = None) -> dict:
    category = meta["category"]
    version = meta.get("version", "v0.1")
    date = meta.get("date", datetime.now().strftime("%Y-%m-%d"))
    image_count = meta.get("image_count", 0)
    batch_count = meta.get("batch_count", 0)
    openai_model = meta.get("openai_model", "gpt-4o")
    claude_model = meta.get("claude_model", "claude-sonnet-4-6")

    if not output_name:
        output_name = f"{category.upper()}_DNA_{version}"

    knowledge_dir = BASE_DIR / "output" / "knowledge"
    json_dir = BASE_DIR / "output" / "json"
    log_dir = BASE_DIR / "output" / "logs"
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    # Build full document
    full_doc = {
        "meta": {
            "category": category,
            "version": version,
            "date": date,
            "image_count": image_count,
            "batch_count": batch_count,
            "providers": {
                "extraction": openai_model,
                "merge": claude_model,
            },
        },
        "dna": dna.get("dna", {}),
        "rules": dna.get("rules", {}),
    }
    if "synthesis_notes" in dna:
        full_doc["synthesis_notes"] = dna["synthesis_notes"]

    # Export JSON
    json_path = json_dir / f"{output_name}.json"
    json_path.write_text(json.dumps(full_doc, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"JSON xuất: {json_path}")

    # Export Markdown
    md_lines = _build_markdown(full_doc, category, version, date, image_count, batch_count, openai_model, claude_model)
    md_path = knowledge_dir / f"{output_name}.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    log(f"Markdown xuất: {md_path}")

    # Extraction log
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "output_name": output_name,
        "meta": full_doc["meta"],
        "md_path": str(md_path),
        "json_path": str(json_path),
    }
    log_path = log_dir / "extraction_log.json"
    existing_logs = []
    if log_path.exists():
        try:
            existing_logs = json.loads(log_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing_logs = []
    existing_logs.append(log_entry)
    log_path.write_text(json.dumps(existing_logs, ensure_ascii=False, indent=2), encoding="utf-8")

    log(f"Hoàn tất! Output: {output_name}.md + {output_name}.json")
    return {"md_path": str(md_path), "json_path": str(json_path)}


def _build_markdown(doc: dict, category: str, version: str, date: str,
                    image_count: int, batch_count: int,
                    openai_model: str, claude_model: str) -> list[str]:
    lines = [
        f"# VENHO AI Studio — {category} DNA",
        f"**Version:** {version} · **Status:** DRAFT  ",
        f"**Generated:** {date} · **Images analyzed:** {image_count} · **Batches:** {batch_count}  ",
        f"**Providers:** {openai_model} (extraction) · {claude_model} (synthesis)",
        "",
        "---",
        "",
    ]

    dna = doc.get("dna", {})

    section_order = [
        ("visual", "Visual DNA"),
        ("material", "Material DNA"),
        ("color", "Color DNA"),
        ("geometry", "Geometry DNA"),
        ("lighting", "Lighting DNA"),
        ("camera_angle", "Camera Angle DNA"),
    ]

    for key, title in section_order:
        section = dna.get(key, {})
        if not section:
            continue

        confidence = section.get("confidence", "")
        badge = _confidence_badge(confidence) if confidence else ""

        lines.append(f"## {title}")
        if badge:
            lines.append(f"*Confidence: {badge}*")
        lines.append("")

        if key == "color":
            palette = section.get("palette", [])
            dominant = section.get("dominant", "")
            if dominant:
                lines.append(f"**Dominant:** {dominant}")
                lines.append("")
            if palette:
                lines.append("| Color |")
                lines.append("|-------|")
                for c in palette:
                    lines.append(f"| {c} |")
        else:
            features = section.get("features", [])
            for f in features:
                lines.append(f"- {f}")

        lines.append("")

    lines += [
        "---",
        "",
        "## Fixed Rules",
        "*(Luôn hiện diện — AI PHẢI include trong mọi generation)*",
        "",
    ]
    for r in doc.get("rules", {}).get("fixed", []):
        lines.append(f"- {r}")
    lines.append("")

    lines += [
        "## Allowed Variations",
        "*(Range thay đổi chấp nhận được)*",
        "",
    ]
    for r in doc.get("rules", {}).get("allowed_variations", []):
        lines.append(f"- {r}")
    lines.append("")

    lines += [
        "## Negative Rules",
        "*(KHÔNG BAO GIỜ xuất hiện trong AI generation)*",
        "",
    ]
    for r in doc.get("rules", {}).get("negative", []):
        lines.append(f"- {r}")
    lines.append("")

    if doc.get("synthesis_notes"):
        lines += [
            "---",
            "",
            "## Synthesis Notes",
            "",
            doc["synthesis_notes"],
            "",
        ]

    lines += [
        "---",
        f"*Generated by VENHO AI Studio — Knowledge Studio {version}*",
    ]

    return lines
