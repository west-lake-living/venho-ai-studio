"""Audit and fail-closed rehydration of QC4G global validation context.

This runner intentionally does not call Validator Studio when the exact image
subject/scenario context is absent.  A face subject is not silently reused as
an image-DNA subject.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from image_studio_runtime.action_composite.workflow_v2 import RegionalGate

ROOT = Path(__file__).resolve().parents[1]
SEARCH = ROOT / "data/identity_restoration_runs/gw-p0-t2-qc4e-local-search"
WINNER = SEARCH / "qc4e-w070-d060"
COMPOSITE = WINNER / "composite/image.png"
BASE = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/action-composite-live/action_01_jogging.png")
RESTORED = WINNER / "artifacts/restored_crop.png"
MASK = ROOT / "data/identity_restoration_runs/gw-p0-t2-qc4c2f-local-candidate/diagnostics/geometry_preserving_mask.png"
A2 = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/face-plates/A2_Front_plate.png")
REPORT_PATH = SEARCH / "qc4g/qc4g-report.json"

EXPECTED = {
    "base": "bb031e7adfcc0c7d79544c3edb932eebafc1f797a59881415e57addc584d26a0",
    "composite": "cc78e635e73e8656b82cd808af0ae837ca88c275f180b3289407dcc9545cd6f0",
    "restored": "fa2b0007c1a8bd336fb17d6903b38758f45b193ee8c78aed9e41f9f33a1be155",
    "mask": "ea7f63bfc72cb8723cfdb480ab45d56917a83aa93ba4cff58441bf56f0d644e2",
    "a2": "1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    manifest = json.loads((WINNER / "composite/manifest.json").read_text(encoding="utf-8"))
    candidate = json.loads((WINNER / "candidate.json").read_text(encoding="utf-8"))
    qc4e1 = json.loads((SEARCH / "qc4e1/qc4e1-report.json").read_text(encoding="utf-8"))
    hashes = {name: sha(path) for name, path in {"base": BASE, "composite": COMPOSITE, "restored": RESTORED, "mask": MASK, "a2": A2}.items()}
    assert hashes == EXPECTED, f"locked artifact mismatch: {hashes}"

    gate = RegionalGate(identity=90.6, eyes_brows=90.0, geometry=96.81,
                        anatomy=100.0, outfit=100.0, environment=100.0,
                        global_composite=None, pixel_preservation=True)
    _, failures = gate.evaluate()
    report = {
        "task": "GW-P0-T2-QC4G",
        "producer": {
            "class": "validator_studio.image_validator.validate_image",
            "path": "validator_studio/image_validator.py:30",
            "required_inputs": ["project", "subject", "image_path", "provider", "samples", "scenario_profile_id"],
            "subject_context_type": "image-DNA subject",
            "dna_reference_context_type": "find_dna_path(project, subject) plus optional scenario overlay",
            "aggregation": "validator_studio.scoring.score_image_observation; configured weighted average in config/validation.yaml",
            "threshold": 90.0,
            "output": "ValidationReport.overall_score",
            "normal_call_path": "validator_studio.validation_pipeline.run_image_validation -> validate_image",
        },
        "context": {
            "subject_context": {"face_subject": "linh_an", "status": "FOUND_AUTHORITATIVE", "source": str(SEARCH / "qc4e1/qc4e1-report.json"), "scope": "face_validator_only"},
            "dna_reference_context": {"a2_front": {"path": str(A2), "sha256": hashes["a2"], "status": "FOUND_AUTHORITATIVE", "scope": "face_validator_only"}, "image_dna": {"status": "MISSING", "reason": "no authoritative image subject/DNA binding in candidate or execution manifest"}},
            "validator_config": {"path": str(ROOT / "config/validation.yaml"), "status": "FOUND_AUTHORITATIVE", "sha256": sha(ROOT / "config/validation.yaml")},
            "recoverability": "MISSING",
            "missing_or_ambiguous_fields": ["image-DNA subject", "image-DNA file binding", "scenario_profile_id", "image-validator reference set", "image-validator provider/model/samples invocation context"],
        },
        "lineage": {
            "candidate_id": candidate["candidate_id"],
            "base_sha256": hashes["base"], "restored_sha256": hashes["restored"], "mask_sha256": hashes["mask"], "composite_sha256": hashes["composite"],
            "manifest_validator_context": manifest.get("validator_context"), "manifest_scene_candidate": manifest.get("scene_candidate"),
            "qc4e1_face_report_available": qc4e1["best_candidate"]["face_validator"]["raw_report"] is not None,
            "source_consistent": True,
        },
        "validation": {"candidate_sha256": hashes["composite"], "provider": None, "model": None, "validation_report_created": False, "validation_report_path": None, "global_composite_score": None, "threshold": 90.0, "status": "BLOCKED", "reason": "exact image-validator semantic context is missing; no validator call made"},
        "regional": {"identity": 90.6, "eyes_brows": 90.0, "geometry": 96.81, "anatomy": 100.0, "outfit": 100.0, "environment": 100.0, "global_composite": None, "regional_gate_status": "BLOCKED", "regional_gate_failures": failures},
        "provenance": {"source_consistent": True, "lineage_complete": False},
        "regression": {"comfyui_rerun": "NO", "image_regenerated": "NO", "thresholds_unchanged": True, "validator_semantics_unchanged": True, "canonical_artifacts_unchanged": True},
        "final": {"global_composite_blocker_resolved": "NO", "QC4_CURRENT_STATE": "BLOCKED", "blockers_remaining": ["authoritative image-DNA subject/reference/scenario context missing"], "GW_P0_T2_READY_FOR_STABILITY_CHECK": "NO"},
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"task": report["task"], "status": report["validation"]["status"], "report": str(REPORT_PATH), "regional_gate": failures}, indent=2))


if __name__ == "__main__":
    main()
