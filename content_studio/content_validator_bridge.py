from __future__ import annotations

from pathlib import Path
from typing import Optional

from content_studio.schemas.content_output import ContentOutput, ValidationInfo
from content_studio.prompt_bridge import slugify


def validate_draft(
    output: ContentOutput,
    markdown_path: Path,
    *,
    prompt_path: Optional[Path] = None,
) -> ValidationInfo:
    if not output.validation.required:
        return output.validation.model_copy(update={"status": "pending", "notes": ["validation not required"]})
    try:
        from validator_studio.content_validator import validate_content
    except Exception as exc:  # noqa: BLE001 - bridge must degrade when M03 is unavailable
        return ValidationInfo(
            required=True,
            status="not_available",
            notes=[f"content validator unavailable: {exc}"],
        )

    subject = output.source_prompt.prompt_id.split("__", 1)[0]
    report = validate_content(
        project=output.project,
        subject=subject,
        draft_path=markdown_path,
        platform=output.content_type.removesuffix("_post"),
        target_language=output.target_language,
        prompt_path=prompt_path,
    )
    verdict = getattr(report.verdict, "value", str(report.verdict)).lower()
    status = "pass"
    if verdict in {"regenerate", "reject", "fail"}:
        status = "fail"
    elif verdict == "revise" or report.issues:
        status = "warning"

    report_file = None
    try:
        from validator_studio.report_builder import write_report

        project_root = markdown_path.parents[2]
        report_id = f"content_{slugify(subject)}_{slugify(markdown_path.stem)}"
        paths = write_report(report, project_root / "validation" / "reports", report_id)
        report_file = str(paths["json"])
    except Exception:
        report_file = None

    return ValidationInfo(
        required=True,
        status=status,
        report_file=report_file,
        notes=[f"validator verdict={verdict}", f"overall_score={report.overall_score}"],
    )
