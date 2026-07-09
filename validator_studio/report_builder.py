from __future__ import annotations

from pathlib import Path

from validator_studio.renderers.validation_report_json import render_validation_report_json
from validator_studio.renderers.validation_report_md import render_validation_report_md
from validator_studio.schemas.validation_base import ValidationReport
from validator_studio.utils import write_json


def write_report(report: ValidationReport, output_dir: Path, report_id: str) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{report_id}.json"
    md_path = output_dir / f"{report_id}.md"
    write_json(json_path, render_validation_report_json(report))
    md_path.write_text(render_validation_report_md(report), encoding="utf-8")
    return {"json": json_path, "md": md_path}

