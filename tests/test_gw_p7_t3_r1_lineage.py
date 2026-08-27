"""GW-P7-T3-R1 evidence-lineage regression checks.

The correction is metadata-only: source bytes and the historical T2 artifact
remain immutable, while the corrective artifact must bind its source SHA to
the bytes it names.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
T1_REPORT = ROOT / "artifacts/identity-restoration/benchmarks/gw-p7-t1-post-remediation-20260826/post_remediation_report.json"
T1_HASH_MANIFEST = ROOT / "artifacts/identity-restoration/benchmarks/gw-p7-t1-post-remediation-20260826/artifact_sha256.json"
T2_CLASSIFICATION = ROOT / "artifacts/identity-restoration/benchmarks/gw-p7-t2-regional-classification-20260827/classification.json"
CORRECTION = ROOT / "artifacts/identity-restoration/benchmarks/gw-p7-t3-r1-lineage-correction-20260827T021930Z/lineage_correction.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_t3_r1_correction_binds_source_sha_to_immutable_report() -> None:
    correction = json.loads(CORRECTION.read_text())
    t1_manifest = json.loads(T1_HASH_MANIFEST.read_text())
    t2 = json.loads(T2_CLASSIFICATION.read_text())
    actual = _sha256(T1_REPORT)

    assert actual == t1_manifest["reportSha256"]
    assert correction["sourceT1ReportActualSha256"] == actual
    assert correction["correctSourceSha256"] == actual
    assert correction["incorrectRecordedSourceSha256"] == t2["sourcePostRemediationReportSha256"]
    assert correction["incorrectRecordedSourceSha256"] != actual
    assert correction["supersedesArtifactSha256"] == _sha256(T2_CLASSIFICATION)
    assert correction["classificationResultPreserved"] is True
    assert correction["regionalFailureCount"] == t2["decision"]["regionalFailureCount"] == 22
    assert correction["rootCause"] == t2["decision"]["rootCause"] == "RC1"
    assert correction["regionalGate"] == t2["decision"]["regionalGate"] == "FAIL"
    assert correction["productionCandidateState"] == t2["decision"]["productionCandidate"] == "REJECTED_QUALITY"


def test_t3_r1_original_t2_rows_and_source_lineage_remain_unchanged() -> None:
    correction = json.loads(CORRECTION.read_text())
    t2 = json.loads(T2_CLASSIFICATION.read_text())
    rows_path = ROOT / t2["sourceRowsPath"]

    assert _sha256(rows_path) == t2["sourceRowsSha256"]
    assert correction["verification"]["t2RowIdsAndNumericScoresMatchSourceRows"] is True
    assert correction["verification"]["failureCountChanged"] is False
    assert correction["verification"]["rootCauseChanged"] is False
    assert correction["verification"]["productionCandidateDecisionChanged"] is False
