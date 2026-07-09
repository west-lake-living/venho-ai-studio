from __future__ import annotations

from validator_studio.prompt_validator import validate_prompt_contract
from validator_studio.schemas.validation_base import Recommendation

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
            sources = contract.get("source_knowledge", [{}])
            env_sources = [s for s in sources if not any(kw in s.get("file", "").lower() for kw in ("linh_an", "character"))]
            primary = (env_sources or sources or [{}])[0]
            subject = str(primary.get("file", "")).removeprefix("VENHO_HOTEL_").removesuffix("_DNA.json").lower() or "lake_view_room"
            report = validate_prompt_contract(
                request.project,
                subject,
                contract,
                prompt_file=contract.get("prompt_id", "(in-memory scene prompt)"),
            )
            reports.append(report.artifact_ref.file)
            if report.verdict == Recommendation.APPROVE:
                statuses.append("pass")
            elif report.verdict == Recommendation.REVISE:
                statuses.append("warning")
            else:
                statuses.append("fail")
        except Exception as exc:  # Validator bridge must degrade while M03 package validation is future work.
            notes.append(f"Scene prompt validation not_available: {exc}")
            return ValidationInfo(required=required, status="not_available", reports=reports, notes=notes)
    if not statuses:
        status = "pending"
    elif any(item == "fail" for item in statuses):
        status = "warning"
        notes.append("One or more scene prompt validations returned fail; treating as warning until video-package validation exists.")
    elif any(item == "warning" for item in statuses):
        status = "warning"
    else:
        status = "pass"
    return ValidationInfo(required=required, status=status, reports=reports, notes=notes)


def write_not_available(required: bool, reason: str) -> ValidationInfo:
    return ValidationInfo(required=required, status="not_available", notes=[reason])
