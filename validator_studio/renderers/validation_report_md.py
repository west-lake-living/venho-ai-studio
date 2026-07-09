from __future__ import annotations

from validator_studio.schemas.validation_base import ValidationReport


def _line_items(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- None"


def render_validation_report_md(report: ValidationReport) -> str:
    forbidden = [
        f"{item.severity.value.upper()} | violated={item.violated} | {item.rule}"
        for item in report.forbidden_violations
    ]
    imperfections = [
        f"present={item.present} | penalized={item.penalized} | {item.item}"
        for item in report.allowed_imperfections_check
    ]
    sections = [
        f"{item.section}/{item.key or '-'}: {item.score:.1f} ({item.status.value}) - {item.reason}"
        for item in report.section_scores
    ]
    issues = [
        f"{item.severity.value.upper()} | {item.issue} Suggestion: {item.suggestion}"
        for item in report.issues
    ]
    categories = [f"{key}: {value:.1f}" for key, value in sorted(report.category_scores.items())]
    return "\n".join([
        "# VALIDATION REPORT",
        "",
        "## META",
        f"- project: {report.project}",
        f"- subject: {report.subject}",
        f"- validation_type: {report.validation_type}",
        f"- artifact: {report.artifact_ref.file}",
        f"- generated_at: {report.generated_at}",
        f"- observer: {report.observer.provider}/{report.observer.model} samples={report.observer.samples}",
        "",
        "## OVERALL SCORE",
        f"- overall_score: {report.overall_score:.1f}",
        f"- verdict: {report.verdict.value}",
        f"- recommendation: {report.recommendation.value}",
        f"- kill_switch: {report.kill_switch.triggered} {report.kill_switch.reason}",
        "",
        "## DNA MATCH SCORE",
        f"- dna_match_score: {report.dna_match_score:.1f}",
        "",
        "## SECTION SCORES",
        _line_items(sections),
        "",
        "## CATEGORY SCORES",
        _line_items(categories),
        "",
        "## FORBIDDEN VIOLATIONS",
        _line_items(forbidden),
        "",
        "## ALLOWED IMPERFECTIONS CHECK",
        _line_items(imperfections),
        "",
        "## ISSUES FOUND",
        _line_items(issues),
        "",
        "## FIX SUGGESTIONS",
        _line_items([item.suggestion for item in report.issues]),
        "",
        "## REGENERATION RECOMMENDATION",
        f"- {report.recommendation.value}",
        "",
        "## VALIDATION NOTES",
        _line_items(report.validation_notes),
        "",
    ])

