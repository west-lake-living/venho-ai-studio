from __future__ import annotations

from pathlib import Path

from validator_studio.schemas.validation_base import ValidationReport
from validator_studio.utils import load_json, write_json


def update_manifest(manifest_path: Path, report: ValidationReport, report_paths: dict[str, Path]) -> None:
    manifest = {"contract_version": "1.0", "module": "validator_studio", "runs": []}
    if manifest_path.exists():
        loaded = load_json(manifest_path)
        if isinstance(loaded, dict):
            manifest.update(loaded)
            manifest.setdefault("runs", [])
    manifest["runs"].append({
        "project": report.project,
        "subject": report.subject,
        "validation_type": report.validation_type,
        "artifact_file": report.artifact_ref.file,
        "artifact_hash": report.artifact_ref.hash,
        "generated_at": report.generated_at,
        "overall_score": report.overall_score,
        "verdict": report.verdict.value,
        "recommendation": report.recommendation.value,
        "kill_switch": report.kill_switch.triggered,
        "report_json": str(report_paths["json"]),
        "report_md": str(report_paths["md"]),
    })
    write_json(manifest_path, manifest)

