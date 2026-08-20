import json
from pathlib import Path


REPORT = Path("data/identity_restoration_runs/gw-p0-t2-qc4-local-candidate/gw-p0-t2-qc4-report.json")


def test_qc4_authority_and_lineage_use_one_candidate_chain():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    authority = report["authority"]
    assert authority["authority_consistent"] is True
    assert report["lineage"]["evidence_source_consistent"] is True
    assert report["geometry_evidence"]["source_sha256"] == authority["final_composite_sha256"]
    assert report["regional"]["geometry"]["source_candidate_sha256"] == authority["restored_crop_sha256"]


def test_qc4_production_pixel_lock_and_byte_difference_are_persisted():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["pixel_preservation"]["production_validator"] == "unchanged_outside_mask"
    assert report["pixel_preservation"]["production_gate"] is True
    assert report["pixel_preservation"]["locked_region"]["changed_pixel_count"] == 0
    assert report["byte_difference"]["different"] is True


def test_qc4_unknown_regions_block_and_base_geometry_score_does_not_leak():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["regional_gate"]["status"] == "BLOCKED"
    assert report["regional_gate"]["gateway_blocker"] == (
        "Regional scores blocked; missing evidence for: anatomy, outfit, environment, global_composite"
    )
    assert report["regional"]["geometry"]["score"] != 17.59
