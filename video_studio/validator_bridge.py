from __future__ import annotations

from pathlib import Path

from validator_studio.prompt_validator import validate_prompt_contract

from video_studio.schemas.video_package import ValidationInfo
from video_studio.schemas.video_request import VideoRequest


def validate_scene_prompts(
    request: VideoRequest,
    scene_prompt_contracts: list[dict],
    *,
    required: bool,
) -> ValidationInfo:
    reports: list[str] = []
    notes: list[str] = ["Video package validation is not available yet; using prompt validation per scene."]
    statuses: list[str] = []
    for contract in scene_prompt_contracts:
        try:
            subject = str(contract.get("source_knowledge", [{}])[-1].get("file", "")).removeprefix("VENHO_HOTEL_")
            subject = subject.removesuffix("_DNA.json").lower() or "lake_view_room"
            report = validate_prompt_contract(
                request.project,
                subject,
                contract,
                prompt_file=contract.get("prompt_id", "(in-memory scene prompt)"),
            )
            reports.append(report.artifact_ref.file)
            statuses.append(report.verdict)
        except Exception as exc:  # Validator bridge must degrade while M03 package validation is future work.
            notes.append(f"Scene prompt validation not_available: {exc}")
            return ValidationInfo(required=required, status="not_available", reports=reports, notes=notes)
    status = "pass" if statuses and all(status in {"pass", "warning"} for status in statuses) else "pending"
    return ValidationInfo(required=required, status=status, reports=reports, notes=notes)


def write_not_available(required: bool, reason: str) -> ValidationInfo:
    return ValidationInfo(required=required, status="not_available", notes=[reason])

