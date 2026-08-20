import json
from pathlib import Path

REPORT = Path("data/identity_restoration_runs/gw-p0-t2-qc4e-local-search/qc4h/qc4h-report.json")


def test_qc4h_semantic_context_is_fail_closed():
    report = json.loads(REPORT.read_text())
    assert report["final"]["authority_state"] == "SEMANTIC_CONTEXT_ABSENT"
    assert report["invocation_manifest"]["created"] == "NO"
    assert report["execution"]["validator_called"] == "NO"


def test_qc4h_does_not_promote_face_context_to_global_context():
    report = json.loads(REPORT.read_text())
    assert report["lineage"]["face_subject"] == "linh_an"
    assert report["lineage"]["face_reference_scope"] == "A2_FRONT only; not promoted to global context"
    assert report["required_fields"]["image_dna_subject"]["status"] == "NOT_FOUND"
    assert report["required_fields"]["reference_set"]["status"] == "NOT_FOUND"


def test_qc4h_sha_first_binding_and_no_mutation():
    report = json.loads(REPORT.read_text())
    assert report["context_lookup"]["base_sha_matches"] is True
    assert report["lineage"]["candidate_sha256"] == "cc78e635e73e8656b82cd808af0ae837ca88c275f180b3289407dcc9545cd6f0"
    assert report["execution"]["canonical_artifacts_unchanged"] is True
