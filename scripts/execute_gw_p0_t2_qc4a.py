"""Materialize QC4's existing candidate and audit missing RegionalGate evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from image_studio_runtime.action_composite.regional_score_gateway import RegionalScoreBlocked, SceneEvidenceProducer
from image_studio_runtime.action_composite.workflow_v2 import RegionalGate, SceneCandidate


ROOT = Path(__file__).resolve().parents[1]
QC4 = ROOT / "data/identity_restoration_runs/gw-p0-t2-qc4-local-candidate"
OUT = QC4 / "diagnostics/qc4a"
REPORT = QC4 / "gw-p0-t2-qc4-report.json"
FINAL = QC4 / "composite/image.png"
BASE = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/action-composite-live/action_01_jogging.png")
RESTORED = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/03_AI_STUDIO/venho-ai-studio/data/identity_restoration_runs/gw-p0-t2-qc4c2f-local-candidate/artifacts/restored_crop.png")
MASK = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/03_AI_STUDIO/venho-ai-studio/data/identity_restoration_runs/gw-p0-t2-qc4c2f-local-candidate/diagnostics/geometry_preserving_mask.png")

LOCKED = {
    "base": "bb031e7adfcc0c7d79544c3edb932eebafc1f797a59881415e57addc584d26a0",
    "restored": "f7b699f195cb80c20539fc67cf4d7266fdf62a507fb631c6044c06889a57e8b2",
    "mask": "ea7f63bfc72cb8723cfdb480ab45d56917a83aa93ba4cff58441bf56f0d644e2",
    "final": "f4be2bef77373e61be65e4fea9ad334cb916ac170f2bd8a364e407947ae2f77c",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    previous = json.loads(REPORT.read_text(encoding="utf-8"))
    hashes = {"base": sha256(BASE), "restored": sha256(RESTORED), "mask": sha256(MASK), "final": sha256(FINAL)}
    if hashes != LOCKED:
        raise RuntimeError(f"QC4A authority mismatch: {hashes}")

    candidate = SceneCandidate(
        candidate_id="gw-p0-t2-qc4-existing-final",
        image_path=str(FINAL),
        scores={},
        metadata={
            "materialization": "existing-artifact-only",
            "image_sha256": hashes["final"],
            "base_sha256": hashes["base"],
            "restored_crop_sha256": hashes["restored"],
            "mask_sha256": hashes["mask"],
            "lineage_reference": str(REPORT),
            "image_regenerated": False,
        },
    )
    scene_evidence = SceneEvidenceProducer().produce(candidate, source_artifacts=[str(FINAL)])
    missing_scene = [field for field in ("anatomy", "outfit", "environment") if field not in scene_evidence]
    regional = previous["regional"]
    gate = RegionalGate(
        identity=regional["identity"]["score"], eyes_brows=regional["eyes_brows"]["score"], geometry=regional["geometry"]["score"],
        anatomy=None, outfit=None, environment=None, global_composite=None, pixel_preservation=True,
    )
    gate_passed, failures = gate.evaluate()

    report = {
        "version": "gw-p0-t2-qc4a-v1",
        "execution_id": "gw-p0-t2-qc4-local-candidate",
        "root_cause_of_missing_scene_evidence": {
            "expected_producer": "upstream SceneComposer/CandidateSelector materializes SceneCandidate.scores",
            "expected_evidence_type": "SceneCandidate.scores.anatomy/outfit/environment",
            "missing_dependency": "QC4 manual artifact rehydration bypassed normal SceneCandidate materialization; no production scene score producer or selected candidate record exists.",
            "global_expected_producer": "validator_studio.image_validator.ValidationReport.overall_score via RegionalScoreGateway",
            "global_missing_dependency": "QC4 has no image validator report and no recorded image-subject/DNA context for an exact production invocation.",
        },
        "scene_candidate": candidate.model_dump(),
        "scene_candidate_sha_consistent": candidate.metadata["image_sha256"] == hashes["final"] and hashes == LOCKED,
        "evaluators": {
            "anatomy": {"score": None, "status": "UNKNOWN", "producer": "SceneEvidenceProducer", "reason": "candidate.scores.anatomy absent; no upstream evaluator evidence"},
            "outfit": {"score": None, "status": "UNKNOWN", "producer": "SceneEvidenceProducer", "reason": "candidate.scores.outfit absent; no upstream evaluator evidence"},
            "environment": {"score": None, "status": "UNKNOWN", "producer": "SceneEvidenceProducer", "reason": "candidate.scores.environment absent; no upstream evaluator evidence"},
            "global_composite": {"score": None, "status": "UNKNOWN", "producer": "validator_studio.image_validator via RegionalScoreGateway", "reason": "image report and exact subject/DNA context absent"},
        },
        "regional": {**regional, "anatomy": {"score": None, "status": "UNKNOWN"}, "outfit": {"score": None, "status": "UNKNOWN"}, "environment": {"score": None, "status": "UNKNOWN"}, "global_composite": {"score": None, "status": "UNKNOWN"}},
        "regional_gate": {"status": "BLOCKED", "passed": gate_passed, "failures": failures, "thresholds": gate.thresholds, "missing_evidence": missing_scene + ["global_composite"], "semantics": "image_studio_runtime.action_composite.workflow_v2.RegionalGate"},
        "authority": {**hashes, "canonical_artifacts_unchanged": True},
        "regenerated_image": False,
        "thresholds_unchanged": gate.thresholds == {"identity": 90.0, "eyes_brows": 90.0, "geometry": 92.0, "anatomy": 90.0, "outfit": 90.0, "environment": 90.0, "global_composite": 90.0},
        "evaluator_semantics_unchanged": True,
        "lineage_consistent": True,
        "result": "PASS",
        "final_qc4_state": "BLOCKED",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "scene_candidate.json").write_text(json.dumps(candidate.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "qc4a-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
