import json
from pathlib import Path

REPORT = Path("data/identity_restoration_runs/gw-p0-t2-qc4e-local-search/qc4g/qc4g-report.json")


def test_qc4g_fails_closed_without_image_context():
    report = json.loads(REPORT.read_text())
    assert report["context"]["recoverability"] == "MISSING"
    assert report["validation"]["validation_report_created"] is False
    assert report["validation"]["global_composite_score"] is None
    assert report["final"]["QC4_CURRENT_STATE"] == "BLOCKED"


def test_qc4g_binds_exact_candidate_and_lineage():
    report = json.loads(REPORT.read_text())
    assert report["lineage"]["candidate_id"] == "qc4e-w070-d060"
    assert report["lineage"]["composite_sha256"] == "cc78e635e73e8656b82cd808af0ae837ca88c275f180b3289407dcc9545cd6f0"
    assert report["provenance"]["source_consistent"] is True
    assert report["provenance"]["lineage_complete"] is False


def test_qc4g_does_not_override_gate_or_thresholds():
    report = json.loads(REPORT.read_text())
    assert report["validation"]["threshold"] == 90.0
    assert report["regional"]["global_composite"] is None
    assert report["regional"]["regional_gate_status"] == "BLOCKED"
    assert report["regression"]["thresholds_unchanged"] is True
