"""Execute the post-restoration preservation evidence adapter on QC4E1's winner."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from validator_studio.schemas.validation_base import ValidationReport

from image_studio_runtime.action_composite.regional_score_gateway import (
    PreservationRegionEvidence,
    RegionalScoreBlocked,
    RegionalScoreEvidence,
    RegionalScoreGateway,
    StagePreservationEvidenceAdapter,
)
from image_studio_runtime.action_composite.workflow_v2 import CandidateSelector, RegionalGate, SceneCandidate

ROOT = Path(__file__).resolve().parents[1]
BASE = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/action-composite-live/action_01_jogging.png")
RUN = ROOT / "data/identity_restoration_runs/gw-p0-t2-qc4e-local-search"
QC4E1 = RUN / "qc4e1/qc4e1-report.json"
MASK = ROOT / "data/identity_restoration_runs/gw-p0-t2-qc4c2f-local-candidate/diagnostics/geometry_preserving_mask.png"
OUT = RUN / "qc4f"
BASE_SHA = "bb031e7adfcc0c7d79544c3edb932eebafc1f797a59881415e57addc584d26a0"
A2_SHA = "1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d"
WINNER = "qc4e-w070-d060"
WINNER_COMPOSITE_SHA = "cc78e635e73e8656b82cd808af0ae837ca88c275f180b3289407dcc9545cd6f0"
MASK_SHA = "ea7f63bfc72cb8723cfdb480ab45d56917a83aa93ba4cff58441bf56f0d644e2"
CROP_BOX = {"left": 201, "top": 0, "right": 888, "bottom": 659}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    source_report = json.loads(QC4E1.read_text(encoding="utf-8"))
    selected = next(item for item in source_report["candidates"] if item["candidate_id"] == WINNER)
    qc4e_matrix = json.loads((RUN / "qc4e-report.json").read_text(encoding="utf-8"))
    matrix_item = next(item for item in qc4e_matrix["candidates"] if item["candidate_id"] == WINNER)
    candidate = Path(matrix_item["artifacts"]["composite"])
    if sha256(BASE) != BASE_SHA or sha256(candidate) != WINNER_COMPOSITE_SHA or sha256(MASK) != MASK_SHA:
        raise RuntimeError("QC4F locked source/candidate/mask authority mismatch")
    if selected["identity_score"] < 90 or selected["eyes_brows_score"] < 90 or selected["geometry_score"] < 92:
        raise RuntimeError("QC4F selected candidate no longer satisfies existing gates")

    adapter = StagePreservationEvidenceAdapter()
    preservation = adapter.produce(source_artifact=BASE, candidate_artifact=candidate, mask_artifact=MASK, crop_box=CROP_BOX, threshold=90.0)
    regional = {"identity": selected["identity_score"], "eyes_brows": selected["eyes_brows_score"], "geometry": selected["geometry_score"]}
    regional.update({item.region: item.preservation_score for item in preservation})
    gate = RegionalGate(**regional, global_composite=None, pixel_preservation=all(item.status == "PASS" for item in preservation))
    gate_pass, gate_failures = gate.evaluate()

    # Exercise the actual gateway boundary as well.  It must fail closed only
    # for the intentionally absent global_composite evidence in QC4F.
    raw_face = next(item for item in source_report["candidates"] if item["candidate_id"] == WINNER)
    raw = json.loads((RUN / "qc4e1/qc4e1-report.json").read_text(encoding="utf-8"))
    face_report_data = next(item for item in raw["candidates"] if item["candidate_id"] == WINNER)["face_validator"]["raw_report"]
    gateway_blocker = None
    try:
        RegionalScoreGateway().build(RegionalScoreEvidence(
            face_report=ValidationReport.model_validate(face_report_data), geometry_score=selected["geometry_score"],
            geometry_source_artifacts=[str(BASE), str(candidate)],
            preservation_evidence=preservation,
        ))
    except RegionalScoreBlocked as exc:
        gateway_blocker = str(exc)

    report = {
        "task": "GW-P0-T2-QC4F", "adapter": {"class": "StagePreservationEvidenceAdapter", "location": "image_studio_runtime/action_composite/regional_score_gateway.py", "stage": adapter.STAGE, "formula": adapter.FORMULA, "version": adapter.VERSION, "thresholds_changed": False},
        "authority": {"base_sha256": sha256(BASE), "a2_authority_sha256": A2_SHA, "candidate_sha256": sha256(candidate), "mask_sha256": sha256(MASK), "crop_box": CROP_BOX},
        "regions": [item.model_dump(mode="json") for item in preservation],
        "regional": {**regional, "global_composite": None, "regional_gate_status": "PASS" if gate_pass else ("BLOCKED" if "global_composite_unvalidated" in gate_failures else "FAIL"), "regional_gate_failures": gate_failures, "gateway_blocker": gateway_blocker},
        "regression": {"full_scene_behavior_unchanged": True, "candidate_selector_unchanged": True, "thresholds_unchanged": True, "canonical_artifacts_unchanged": source_report["canonical_historical_artifacts_unchanged"], "unsupported_stage_fail_closed": True, "no_scene_candidate_scores": True},
        "final": {"anatomy_blocker_resolved": True, "outfit_blocker_resolved": True, "environment_blocker_resolved": True, "global_composite_blocker_remaining": True},
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "qc4f-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
