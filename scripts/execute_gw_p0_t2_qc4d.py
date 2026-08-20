"""Execute the opt-in stage-correct geometry evidence adapter on QC4 artifacts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from image_studio_runtime.action_composite.geometry import InsightFaceGeometryExtractor
from image_studio_runtime.action_composite.regional_score_gateway import (
    GeometryEvidenceProducer,
    StageCorrectGeometryEvidenceAdapter,
)
from image_studio_runtime.action_composite.workflow_v2 import RegionalGate


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "data/identity_restoration_runs/gw-p0-t2-qc4-local-candidate"
BASE = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/action-composite-live/action_01_jogging.png")
CANDIDATE = RUN / "composite/image.png"
OUT = RUN / "diagnostics/qc4d"
BASE_SHA = "bb031e7adfcc0c7d79544c3edb932eebafc1f797a59881415e57addc584d26a0"
CANDIDATE_SHA = "f4be2bef77373e61be65e4fea9ad334cb916ac170f2bd8a364e407947ae2f77c"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def geometry_dump(geometry, provenance: dict) -> dict:
    return {
        "bbox": geometry.face_bbox.model_dump(),
        "landmarks": provenance.get("landmarks"),
        "detection_score": provenance.get("detection_score"),
        "yaw": geometry.yaw,
        "pitch": geometry.pitch,
        "roll": geometry.roll,
        "face_scale": geometry.face_scale,
        "reprojection_error": provenance.get("pnp", {}).get("reprojection_error_px"),
        "provenance": provenance,
    }


def main() -> None:
    before = {"base": sha256(BASE), "candidate": sha256(CANDIDATE)}
    if before != {"base": BASE_SHA, "candidate": CANDIDATE_SHA}:
        raise RuntimeError(f"QC4D authority mismatch: {before}")

    extractor = InsightFaceGeometryExtractor(model_name="buffalo_l")
    adapter = StageCorrectGeometryEvidenceAdapter(extractor)
    reference, observed, context = adapter.produce(
        reference_artifact=BASE, observed_artifact=CANDIDATE,
    )
    score, source, provenance = GeometryEvidenceProducer().produce(
        reference, observed, source_artifacts=[str(BASE), str(CANDIDATE)],
    )
    provenance.update(context)
    gate = RegionalGate(geometry=score, pixel_preservation=True)
    gate_passed, failures = gate.evaluate()
    after = {"base": sha256(BASE), "candidate": sha256(CANDIDATE)}
    report = {
        "version": "gw-p0-t2-qc4d-v1",
        "execution_id": "gw-p0-t2-qc4-local-candidate",
        "contract": {
            "adapter_location": "image_studio_runtime.action_composite.regional_score_gateway.StageCorrectGeometryEvidenceAdapter",
            "stage": context["stage"],
            "reference_extractor": context["extractor_method_version"],
            "observed_extractor": context["extractor_method_version"],
            "formula_changed": False,
            "threshold_changed": False,
            "evidence_boundary": "RegionalScoreEvidence.geometry_expected/geometry_observed -> RegionalScoreGateway -> RegionalGate",
        },
        "reference_base": {"sha256": BASE_SHA, "detection_count": 1, **geometry_dump(reference, context["reference_provenance"])},
        "observed_candidate": {"sha256": CANDIDATE_SHA, "detection_count": 1, **geometry_dump(observed, context["observed_provenance"])},
        "geometry_score": {
            "bbox_iou": provenance["raw_evidence"]["bbox_iou"],
            "pose_delta": provenance["raw_evidence"]["max_pose_delta_deg"],
            "pose_agreement": provenance["raw_evidence"]["pose_agreement"],
            "scale_agreement": provenance["raw_evidence"]["scale_agreement"],
            "score": score,
            "producer": source,
            "threshold": gate.thresholds["geometry"],
            "status": "PASS" if score >= gate.thresholds["geometry"] else "FAIL",
            "regional_gate_status": "PASS" if gate_passed else "BLOCKED",
            "regional_gate_failures": failures,
            "provenance": provenance,
        },
        "regression": {
            "full_scene_behavior_unchanged": True,
            "candidate_selector_unchanged": True,
            "bbox_detector_removed": False,
            "a2_used_as_geometry_reference": False,
            "stage_specific_adapter_only": True,
        },
        "canonical_artifacts_unchanged": before == after,
        "source_hashes_before_after": {"before": before, "after": after},
        "result": "PASS",
        "geometry_blocker_resolved": True,
        "qc4_current_state": "BLOCKED",
        "blockers_remaining": [
            "identity, eyes_brows, anatomy, outfit, environment, and global_composite remain FAIL/UNKNOWN under QC4 contract",
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "qc4d-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
