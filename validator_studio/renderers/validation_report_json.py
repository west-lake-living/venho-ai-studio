from __future__ import annotations

from validator_studio.schemas.validation_base import ValidationReport


def render_validation_report_json(report: ValidationReport) -> dict:
    return report.model_dump(mode="json")

