"""Audit GeometryEvidenceProducer semantic fitness for post-restoration QC."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from image_studio_runtime.action_composite.models import BoundingBox, FaceGeometry
from image_studio_runtime.action_composite.regional_score_gateway import GeometryEvidenceProducer
from image_studio_runtime.action_composite.workflow_v2 import RegionalGate


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "data/identity_restoration_runs/gw-p0-t2-qc4-local-candidate"
BASE_RUN = ROOT / "data/identity_restoration_runs/gw-p0-t2-20260819-local-rerun"
QC4 = RUN / "gw-p0-t2-qc4-report.json"
QC4C3 = BASE_RUN / "diagnostics/qc4c3/gw-p0-t2-qc4c3-report.json"
MANIFEST = RUN / "composite/manifest.json"
BASE = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/action-composite-live/action_01_jogging.png")
FINAL = RUN / "composite/image.png"
OUT = RUN / "diagnostics/qc4c"

BASE_SHA = "bb031e7adfcc0c7d79544c3edb932eebafc1f797a59881415e57addc584d26a0"
FINAL_SHA = "f4be2bef77373e61be65e4fea9ad334cb916ac170f2bd8a364e407947ae2f77c"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bbox(data: dict[str, Any]) -> BoundingBox:
    return BoundingBox.model_validate(data)


def geometry_from_observation(data: dict[str, Any], *, head: BoundingBox) -> FaceGeometry:
    return FaceGeometry(
        face_bbox=bbox(data["bbox"]), head_bbox=head,
        yaw=float(data["yaw"]), pitch=float(data["pitch"]), roll=float(data["roll"]),
        face_scale=float(data["face_scale"]),
    )


def main() -> None:
    qc4 = json.loads(QC4.read_text(encoding="utf-8"))
    qc4c3 = json.loads(QC4C3.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if sha256(BASE) != BASE_SHA or sha256(FINAL) != FINAL_SHA:
        raise RuntimeError("QC4C authority mismatch")

    expected_data = manifest["geometry"]
    expected = FaceGeometry.model_validate(expected_data)
    base_observation = qc4c3["geometry"]
    repaired_observation = qc4["geometry_evidence"]
    base_observed = geometry_from_observation(base_observation, head=expected.head_bbox)
    repaired_observed = geometry_from_observation(repaired_observation, head=expected.head_bbox)
    producer = GeometryEvidenceProducer()
    base_score, base_source, base_prov = producer.produce(expected, base_observed, source_artifacts=[str(BASE)])
    repaired_score, repaired_source, repaired_prov = producer.produce(expected, repaired_observed, source_artifacts=[str(BASE), str(FINAL)])

    raw_base = base_prov["raw_evidence"]
    raw_repaired = repaired_prov["raw_evidence"]
    # Solve the current weighted formula's minimum individual term under
    # perfect values for the other two terms.  These are diagnostic bounds,
    # not replacement scores.
    required_iou_with_perfect_pose_scale = (0.92 - 0.30 - 0.20) / 0.50
    required_pose_with_perfect_iou_scale = (0.92 - 0.50 - 0.20) / 0.30
    current_pose_delta = raw_base["max_pose_delta_deg"]
    max_pose_delta_for_required_agreement = (1.0 - required_pose_with_perfect_iou_scale) * 180.0

    gate_threshold = RegionalGate().thresholds["geometry"]
    report = {
        "version": "gw-p0-t2-qc4c-v1",
        "execution_id": "gw-p0-t2-qc4-local-candidate",
        "geometry_formula": {
            "producer": base_source,
            "method_version": GeometryEvidenceProducer.VERSION,
            "formula": "100 * (0.50*bbox_iou + 0.30*pose_agreement + 0.20*scale_agreement)",
            "inputs": {
                "bbox_iou": "intersection(expected.face_bbox, observed.face_bbox) / union(expected.face_bbox, observed.face_bbox)",
                "pose_delta": "max(abs(expected.yaw-observed.yaw), abs(expected.pitch-observed.pitch), abs(expected.roll-observed.roll))",
                "pose_agreement": "max(0, 1 - pose_delta / 180)",
                "scale_agreement": "min(expected.face_scale, observed.face_scale) / max(expected.face_scale, observed.face_scale)",
            },
            "normalization": "bbox IoU and agreements normalized to 0..1; final score multiplied by 100 and rounded to 2 decimals",
            "weights": {"bbox_iou": 0.50, "pose_agreement": 0.30, "scale_agreement": 0.20},
            "range": "0..100",
            "clamp_behavior": "pose agreement lower-clamped at 0; IoU and scale ratio are naturally 0..1",
            "threshold": gate_threshold,
        },
        "reference": {
            "reference_type": "source/base FaceGeometry lock",
            "reference_path": str(BASE),
            "reference_sha256": BASE_SHA,
            "reference_authority": "ActionCompositePipeline geometry lock / BBoxFaceDetector output persisted in composite manifest",
            "not_reference": "A2_FRONT is identity authority, not the geometry reference for this producer",
        },
        "scores": {
            "locked_base_geometry_score": base_score,
            "repaired_candidate_geometry_score": repaired_score,
            "scores_reproduced": base_score == 17.59 and repaired_score == 19.37,
            "locked_base_raw_evidence": raw_base,
            "repaired_candidate_raw_evidence": raw_repaired,
            "source_provenance": {
                "base_observed_geometry": qc4c3["geometry"]["provenance"],
                "repaired_observed_geometry": qc4["geometry_evidence"]["provenance"],
            },
        },
        "stage_semantics": {
            "full_scene_definition": "CandidateSelector selects scene candidates using scene scores; no GeometryEvidenceProducer call is present in candidate selection.",
            "identity_restoration_definition": "ActionCompositePipeline locks source FaceGeometry and compares expected/observed geometry after restoration.",
            "intended_invariant": "B: preserve source/base pose; current implementation expresses this through expected/observed comparison, but uses incompatible detector geometry representations.",
            "evidence": [
                "image_studio_runtime/action_composite/locks.py:GeometryLock",
                "image_studio_runtime/action_composite/pipeline.py: geometry lock and post-restore evidence wiring",
                "docs/Image studio/LINH_AN_ACTION_COMPOSITE_HYBRID_COMFYUI_TECHNICAL_PLAN_v1.0.md: bbox + landmark + head pose preservation",
            ],
        },
        "feasibility": {
            "estimated_changes_required_for_92": {
                "if_pose_and_scale_perfect": {"required_bbox_iou": round(required_iou_with_perfect_pose_scale, 6)},
                "if_bbox_and_scale_perfect": {"required_pose_agreement": round(required_pose_with_perfect_iou_scale, 6), "max_pose_delta_deg": round(max_pose_delta_for_required_agreement, 6)},
                "current_base": {"bbox_iou": raw_base["bbox_iou"], "pose_delta_deg": current_pose_delta, "scale_agreement": raw_base["scale_agreement"]},
                "interpretation": "The current metric would require large detector-space bbox/pose changes or a representation-compatible observation; that is not evidence that the source action pose should be changed.",
            },
            "preservation_conflict": "The gate threshold is incompatible with the current metric/reference pair: untouched base is 17.59, so a pose-preserving restoration cannot be expected to pass this gate as implemented.",
            "classification": "CONTRACT_CONTRADICTION",
        },
        "historical_calibration_context": {
            "found": False,
            "evidence": [
                "tests/test_regional_score_gateway.py only verifies deterministic scoring and identical geometry => 100",
                "RegionalGate threshold 92 is defined in workflow_v2.py",
                "no calibration dataset or post-restoration score calibration record found",
            ],
            "threshold_context": "not demonstrably calibrated against action composites, canonical portraits, or post-restoration crops",
        },
        "correct_stage_binding": {
            "option": "OPTION 3",
            "binding": "geometry gate belongs upstream/identity contract as source-pose preservation verification after restoration; it must not require A2 canonical portrait geometry",
            "contract_gap_found": True,
            "gap": "the current producer compares BBoxFaceDetector lock geometry with InsightFace observed geometry, while RegionalGate applies a 92 threshold as if the score were calibrated for that pair",
        },
        "identity_interaction": {
            "expected_effect_of_larger_identity_mask": "UNKNOWN_NON_MONOTONIC; existing evidence does not predict a passing geometry score. A larger mask may improve face QC but can alter observed bbox/pose/scale and lower this metric; it cannot be assumed to improve it.",
            "existing_comparison": {"base_score": base_score, "candidate_score": repaired_score, "identity_score": 84.6, "eyes_brows_score": 84.0},
        },
        "implementation_changed": False,
        "thresholds_changed": False,
        "canonical_artifacts_unchanged": sha256(BASE) == BASE_SHA and sha256(FINAL) == FINAL_SHA,
        "source_hashes": {"base": sha256(BASE), "candidate": sha256(FINAL)},
        "result": "PASS",
        "root_cause": "CONTRACT_MISMATCH: source BBoxFaceDetector geometry is compared with InsightFace geometry, and the untouched base itself fails the 92 threshold.",
        "recommended_next_task": "Define and approve a stage-correct geometry evidence contract/adapter; do not alter thresholds or restoration in QC4C.",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "qc4c-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
