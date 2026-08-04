from __future__ import annotations

from pathlib import Path

from validator_studio.alignment_validator import validate_alignment
from validator_studio.claim_validator import ClaimValidator
from validator_studio.content_validator import validate_content
from validator_studio.schemas.validation_base import Recommendation


class M03ValidatorBridge:
    """Claim + alignment + scored content gate for a generated copy candidate.

    validate_content() is the real weighted rubric (brand_fit/tone/clarity/
    cta/language_fit -> 0-100 overall score -> approve/revise/regenerate/
    reject, see validator_studio.scoring.verdict_for_score) -- Harry's rule
    ("bài viết phải được chấm điểm Validator, không pass phải làm lại", added
    2026-08-04) is enforced here: only Recommendation.APPROVE counts as
    passing; anything else forces verdict="NEEDS_REVISION" so daily_cycle's
    retry loop regenerates the draft instead of queuing it for approval.
    """

    def validate_package(self, brief: dict, copy_candidate: dict) -> dict:
        claim_report = ClaimValidator().validate([{"text": c, "fact_key": None} if isinstance(c, str) else c for c in copy_candidate.get("claims", [])])
        alignment_report = validate_alignment(brief, copy_candidate.get("scene_summary", {}))
        verdict = "READY_FOR_REVIEW"
        content_report = None

        markdown_path = copy_candidate.get("content_package_paths", {}).get("markdown")
        dna_subject = copy_candidate.get("dna_subject")
        project = brief.get("project")
        content_report_failed = False
        if markdown_path and dna_subject and project:
            try:
                content_report = validate_content(
                    project,
                    dna_subject,
                    Path(markdown_path),
                    platform=copy_candidate.get("platform", "facebook"),
                    target_language=copy_candidate.get("language"),
                )
            except Exception:  # noqa: BLE001 - Part 2.1 invariant #8: validator crash/malformed input must fail-closed to UNVALIDATED, never silently pass as APPROVED
                content_report_failed = True

        if content_report_failed or "UNVALIDATED" in {claim_report["verdict"], alignment_report["verdict"]}:
            verdict = "UNVALIDATED"
        elif claim_report["kill_switches"] or alignment_report["kill_switches"]:
            verdict = "NEEDS_REVISION"
        elif content_report is not None and content_report.verdict != Recommendation.APPROVE:
            verdict = "NEEDS_REVISION"

        reports = [claim_report, alignment_report]
        if content_report is not None:
            reports.append(content_report.model_dump(mode="json"))
        return {"verdict": verdict, "reports": reports}
