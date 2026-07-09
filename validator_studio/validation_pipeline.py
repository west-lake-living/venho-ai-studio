from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from validator_studio.image_validator import validate_image
from validator_studio.face_validator import validate_face
from validator_studio.content_validator import validate_content
from validator_studio.prompt_validator import validate_prompt
from validator_studio.prompt_resolver import resolve_latest_prompt_path
from validator_studio.report_builder import write_report
from validator_studio.validation_manifest import update_manifest
from validator_studio.utils import BASE_DIR


def _report_id(validation_type: str, subject: str, artifact_hash: Optional[str]) -> str:
    suffix = (artifact_hash or "nohash").replace("sha256:", "")[:12]
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{validation_type}_{subject}_{suffix}_{stamp}"


def _output_paths(project: str) -> tuple[Path, Path]:
    root = BASE_DIR / "data" / "projects" / project / "validation"
    return root / "reports", root / "validation_manifest.json"


def run_image_validation(
    project: str,
    subject: str,
    image_path: Path,
    prompt_path: Optional[Path] = None,
    provider: str = "mock",
    samples: Optional[int] = None,
) -> dict[str, Path]:
    report = validate_image(project, subject, image_path, prompt_path, provider, samples)
    reports_dir, manifest_path = _output_paths(project)
    paths = write_report(report, reports_dir, _report_id("image", subject, report.artifact_ref.hash))
    update_manifest(manifest_path, report, paths)
    return paths


def run_prompt_validation(project: str, subject: str, prompt_path: Path) -> dict[str, Path]:
    report = validate_prompt(project, subject, prompt_path)
    reports_dir, manifest_path = _output_paths(project)
    paths = write_report(report, reports_dir, _report_id("prompt", subject, report.artifact_ref.hash))
    update_manifest(manifest_path, report, paths)
    return paths


def run_latest_prompt_validation(
    project: str,
    subject: str,
    prompt_type: str,
    brief_slug: Optional[str] = None,
) -> dict[str, Path]:
    prompt_path = resolve_latest_prompt_path(project, subject, prompt_type, brief_slug)
    return run_prompt_validation(project, subject, prompt_path)


def run_face_validation(
    project: str,
    subject: str,
    image_path: Path,
    provider: str = "mock",
) -> dict[str, Path]:
    report = validate_face(project, subject, image_path, provider)
    reports_dir, manifest_path = _output_paths(project)
    paths = write_report(report, reports_dir, _report_id("face", subject, report.artifact_ref.hash))
    update_manifest(manifest_path, report, paths)
    return paths


def run_content_validation(
    project: str,
    subject: str,
    draft_path: Path,
    platform: str = "facebook",
    target_language: Optional[str] = None,
    prompt_path: Optional[Path] = None,
) -> dict[str, Path]:
    report = validate_content(project, subject, draft_path, platform, target_language, prompt_path)
    reports_dir, manifest_path = _output_paths(project)
    paths = write_report(report, reports_dir, _report_id("content", subject, report.artifact_ref.hash))
    update_manifest(manifest_path, report, paths)
    return paths
