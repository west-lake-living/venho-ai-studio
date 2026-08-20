"""Resolve QC4H global-validation authority without invoking a validator."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEARCH = ROOT / "data/identity_restoration_runs/gw-p0-t2-qc4e-local-search"
WINNER = SEARCH / "qc4e-w070-d060"
BASE = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/action-composite-live/action_01_jogging.png")
COMPOSITE = WINNER / "composite/image.png"
OUT = SEARCH / "qc4h/qc4h-report.json"
EXPECTED_BASE = "bb031e7adfcc0c7d79544c3edb932eebafc1f797a59881415e57addc584d26a0"
EXPECTED_COMPOSITE = "cc78e635e73e8656b82cd808af0ae837ca88c275f180b3289407dcc9545cd6f0"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    base_sha, candidate_sha = sha(BASE), sha(COMPOSITE)
    assert base_sha == EXPECTED_BASE
    assert candidate_sha == EXPECTED_COMPOSITE
    validation_config = ROOT / "config/validation.yaml"
    manifest = WINNER / "composite/manifest.json"
    candidate = WINNER / "candidate.json"
    report = {
        "task": "GW-P0-T2-QC4H",
        "context_lookup": {
            "base_sha_matches": True,
            "originating_record_found": False,
            "authoritative_sources": [
                {"path": str(manifest), "authority": "execution artifact manifest", "scope": "restoration/candidate lineage", "sha256": sha(manifest)},
                {"path": str(candidate), "authority": "candidate execution record", "scope": "restoration parameters and invariants", "sha256": sha(candidate)},
                {"path": str(SEARCH / "qc4e1/qc4e1-report.json"), "authority": "QC report", "scope": "Face Validator only"},
                {"path": str(validation_config), "authority": "project configuration", "scope": "generic validator weights/default samples", "sha256": sha(validation_config)},
            ],
        },
        "required_fields": {
            "project": {"status": "NOT_FOUND", "value_or_id": None, "authority_source": None, "version_hash": None},
            "image_dna_subject": {"status": "NOT_FOUND", "value_or_id": None, "authority_source": None, "version_hash": None},
            "reference_set": {"status": "NOT_FOUND", "value_or_id": None, "authority_source": None, "version_hash": None},
            "scenario_profile": {"status": "NOT_FOUND", "value_or_id": None, "authority_source": None, "version_hash": None},
            "provider": {"status": "NOT_FOUND", "value_or_id": None, "authority_source": None, "version_hash": None, "note": "comfyui-local is restoration provider, not image-validator provider"},
            "samples": {"status": "DERIVABLE_FROM_AUTHORITATIVE_SOURCE", "value_or_id": 1, "authority_source": str(validation_config), "version_hash": sha(validation_config), "note": "generic default only; invocation was not recorded"},
            "validator_config": {"status": "FOUND_AUTHORITATIVE", "value_or_id": str(validation_config), "authority_source": str(validation_config), "version_hash": sha(validation_config)},
            "invocation_metadata": {"status": "NOT_FOUND", "value_or_id": None, "authority_source": None, "version_hash": None},
        },
        "reference_set": {"references": [], "roles": [], "hashes": [], "status": "NOT_FOUND"},
        "authority": {"conflicts": [], "precedence_applied": "SHA-first lookup; execution artifact > candidate record > QC report; no semantic global context record exists", "selected_authority": None, "rejected_authority": []},
        "lineage": {"base_sha256": base_sha, "candidate_sha256": candidate_sha, "candidate_id": "qc4e-w070-d060", "face_subject": "linh_an", "face_reference_scope": "A2_FRONT only; not promoted to global context", "source_consistent": True},
        "invocation_manifest": {"created": "NO", "path": None, "sha256": None, "reason": "mandatory semantic fields are not authoritative"},
        "execution": {"validator_called": "NO", "image_regenerated": "NO", "comfyui_rerun": "NO", "thresholds_changed": "NO", "canonical_artifacts_unchanged": True},
        "final": {"authority_state": "SEMANTIC_CONTEXT_ABSENT", "missing_authoritative_fields": ["project binding for global validator", "image-DNA subject", "reference-set ID/version/hash", "scenario profile ID/version/hash", "image-validator provider/model invocation", "invocation metadata"], "human_authority_required": "YES", "recommended_next_task": "Approve and persist one canonical image-DNA subject, scenario profile, and global reference-set binding for action_01_jogging before QC4I."},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"task": report["task"], "authority_state": report["final"]["authority_state"], "report": str(OUT), "validator_called": "NO"}, indent=2))


if __name__ == "__main__":
    main()
