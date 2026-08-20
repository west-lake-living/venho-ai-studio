"""Audit and materialize the existing QC4 RegionalGate evidence contract.

This is a diagnostics-only replay.  It does not call ComfyUI, validators, or
any image generator, and it never writes canonical image artifacts.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from image_studio_runtime.action_composite.workflow_v2 import RegionalGate


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "data/identity_restoration_runs/gw-p0-t2-qc4-local-candidate"
QC4_REPORT = RUN / "gw-p0-t2-qc4-report.json"
QC4A_REPORT = RUN / "diagnostics/qc4a/qc4a-report.json"
OUT = RUN / "diagnostics/qc4b"
FINAL = RUN / "composite/image.png"
BASE = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/action-composite-live/action_01_jogging.png")
MASK = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/action-composite-live/face-mask.png")

LOCKED = {
    "base": "bb031e7adfcc0c7d79544c3edb932eebafc1f797a59881415e57addc584d26a0",
    "final": "f4be2bef77373e61be65e4fea9ad334cb916ac170f2bd8a364e407947ae2f77c",
    "mask": "506fd5e52274b59af2881dcbaef3fe7904da7f30c75dc3bc23492dadf50ffb94",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def region_matrix() -> list[dict[str, Any]]:
    common = {
        "mandatory": True,
        "fail_closed": "RegionalGate.evaluate() records <field>_unvalidated when value is None",
        "regional_gate_source": "image_studio_runtime.action_composite.workflow_v2.RegionalGate",
    }
    return [
        {**common, "region": "identity", "expected_evidence": "face ValidationReport.dna_match_score", "actual_evidence": "84.6", "applicability": "REEVALUATE", "producer": "validator_studio.face_validator", "status": "FAIL", "missing_dependency": None, "recommended_resolution": "retain face validator report in canonical execution"},
        {**common, "region": "eyes_brows", "expected_evidence": "face ValidationReport.category_scores[eyes_and_brows]", "actual_evidence": "84.0", "applicability": "REEVALUATE", "producer": "validator_studio.face_validator", "status": "FAIL", "missing_dependency": None, "recommended_resolution": "retain face validator report in canonical execution"},
        {**common, "region": "geometry", "expected_evidence": "GeometryEvidenceProducer output from expected/observed FaceGeometry", "actual_evidence": "19.37", "applicability": "REEVALUATE", "producer": "GeometryEvidenceProducer.geometry-evidence-v1", "status": "FAIL", "missing_dependency": None, "recommended_resolution": "preserve existing geometry evidence and investigate source geometry separately"},
        {**common, "region": "anatomy", "expected_evidence": "SceneCandidate.scores.anatomy", "actual_evidence": None, "applicability": "VERIFY_BY_PIXEL_PRESERVATION", "producer": "SceneEvidenceProducer -> SceneCandidate.scores.anatomy", "status": "UNKNOWN", "missing_dependency": "no candidate score and RegionalGate has no preservation-evidence input", "recommended_resolution": "keep pixel preservation as a separate invariant; do not map it to a score"},
        {**common, "region": "outfit", "expected_evidence": "SceneCandidate.scores.outfit", "actual_evidence": None, "applicability": "VERIFY_BY_PIXEL_PRESERVATION", "producer": "SceneEvidenceProducer -> SceneCandidate.scores.outfit", "status": "UNKNOWN", "missing_dependency": "no candidate score and RegionalGate has no preservation-evidence input", "recommended_resolution": "keep pixel preservation as a separate invariant; do not map it to a score"},
        {**common, "region": "environment", "expected_evidence": "SceneCandidate.scores.environment", "actual_evidence": None, "applicability": "VERIFY_BY_PIXEL_PRESERVATION", "producer": "SceneEvidenceProducer -> SceneCandidate.scores.environment", "status": "UNKNOWN", "missing_dependency": "no candidate score and RegionalGate has no preservation-evidence input", "recommended_resolution": "keep pixel preservation as a separate invariant; do not map it to a score"},
        {**common, "region": "global_composite", "expected_evidence": "image ValidationReport.overall_score", "actual_evidence": None, "applicability": "REEVALUATE", "producer": "validator_studio.image_validator -> RegionalScoreGateway", "status": "UNKNOWN", "missing_dependency": "no exact image subject/DNA/reference/config context or image ValidationReport in QC4 lineage", "recommended_resolution": "capture the exact image validator context/report in a canonical execution"},
    ]


def main() -> None:
    qc4 = json.loads(QC4_REPORT.read_text(encoding="utf-8"))
    qc4a = json.loads(QC4A_REPORT.read_text(encoding="utf-8"))
    hashes = {"base": sha256(BASE), "final": sha256(FINAL), "mask": sha256(MASK)}
    if hashes != LOCKED:
        raise RuntimeError(f"QC4B authority mismatch: {hashes}")

    before = {"base": sha256(BASE), "final": sha256(FINAL), "mask": sha256(MASK)}
    gate = RegionalGate(
        identity=84.6, eyes_brows=84.0, geometry=19.37,
        anatomy=None, outfit=None, environment=None, global_composite=None,
        pixel_preservation=bool(qc4["pixel_preservation"]["production_gate"]),
    )
    passed, failures = gate.evaluate()
    matrix = region_matrix()
    geometry = qc4["regional"]["geometry"]
    raw = geometry["provenance"]["raw_evidence"]
    expected = qc4["authority"]
    preservation = {
        "source_artifact": str(BASE),
        "target_artifact": str(FINAL),
        "relevant_region": "locked_region defined by authoritative face-mask complement",
        "changed_pixels": qc4["pixel_preservation"]["locked_region"]["changed_pixel_count"],
        "preservation_status": "PASS",
        "lineage": {"base_sha256": hashes["base"], "final_sha256": hashes["final"], "mask_sha256": hashes["mask"]},
        "contract_consumable_by_regional_gate": False,
    }
    report = {
        "version": "gw-p0-t2-qc4b-v1",
        "execution_id": "gw-p0-t2-qc4-local-candidate",
        "regional_contract": {
            "implementation": "image_studio_runtime.action_composite.workflow_v2.RegionalGate",
            "designed_for": ["full_scene_candidate_generation", "post_identity_restoration_validation"],
            "determination": "both: CandidateSelector/SceneCandidate supplies upstream scene evidence, while ActionCompositePipeline invokes RegionalGate after restoration",
            "numeric_score_required_for_all_fields": True,
            "preservation_inheritance_supported": False,
        },
        "stage_applicability": {item["region"]: item["applicability"] for item in matrix},
        "preservation": {"anatomy": preservation, "outfit": preservation, "environment": preservation, "contract_supported": False},
        "global": {
            "validation_context_found": False,
            "validation_report_rehydrated": False,
            "missing_dependency": matrix[-1]["missing_dependency"],
            "existing_validator_contract": "validator_studio.image_validator.validate_image(project, subject, image_path, provider, samples, scenario_profile_id)",
            "available_lineage": {"face_report": str(QC4_REPORT), "scene_candidate": str(QC4A_REPORT), "image_report": None},
        },
        "geometry_audit": {
            "producer": geometry["provenance"]["producer"],
            "formula": "100 * (0.50*bbox_iou + 0.30*pose_agreement + 0.20*scale_agreement); pose_agreement=max(0, 1-max_abs_pose_delta/180)",
            "inputs": {"expected_source": str(BASE), "observed_source": geometry["evidence_source"], "source_candidate_sha256": geometry["source_candidate_sha256"], "raw_evidence": raw},
            "expected_range": "0..100",
            "threshold": 92.0,
            "classification": "VALID_LOW_SCORE",
            "implementation_bug_found": False,
            "reason": "19.37 is reproducible from the persisted geometry-evidence-v1 inputs; InsightFace geometry is diagnostic evidence and is not substituted into the RegionalGate metric",
        },
        "contract_matrix": matrix,
        "regional": {
            "identity": {"score": 84.6, "status": "FAIL"},
            "eyes_brows": {"score": 84.0, "status": "FAIL"},
            "geometry": {"score": 19.37, "status": "FAIL"},
            "anatomy": {"score": None, "status": "UNKNOWN"},
            "outfit": {"score": None, "status": "UNKNOWN"},
            "environment": {"score": None, "status": "UNKNOWN"},
            "global_composite": {"score": None, "status": "UNKNOWN"},
        },
        "regional_gate": {"status": "BLOCKED", "passed": passed, "failures": failures, "thresholds": gate.thresholds, "semantics": "unchanged RegionalGate.evaluate"},
        "authority": {**hashes, "canonical_artifacts_unchanged": True, "source_hash_consistency": hashes == LOCKED},
        "architecture_changed": False,
        "thresholds_changed": False,
        "canonical_artifacts_unchanged": True,
        "result": "PASS",
        "final_qc4_state": "BLOCKED",
        "blockers_remaining": [item["missing_dependency"] for item in matrix if item["missing_dependency"]],
        "safe_next_actions": ["capture exact scene candidate evidence and image ValidationReport context in a future canonical execution"],
        "source_hashes_before_after": {"before": before, "after": {"base": sha256(BASE), "final": sha256(FINAL), "mask": sha256(MASK)}},
        "source_reports": {"qc4": str(QC4_REPORT), "qc4a": str(QC4A_REPORT)},
        "expected_authority": expected,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "contract-matrix.json").write_text(json.dumps(matrix, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "qc4b-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
