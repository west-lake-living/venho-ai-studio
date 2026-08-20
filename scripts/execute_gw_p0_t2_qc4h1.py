"""Persist the human-approved QC4H1 authority decision, fail-closed if references are absent."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEARCH = ROOT / "data/identity_restoration_runs/gw-p0-t2-qc4e-local-search"
OUT = SEARCH / "qc4h1/qc4h1-authority-record.json"
BASE = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/action-composite-live/action_01_jogging.png")
COMPOSITE = SEARCH / "qc4e-w070-d060/composite/image.png"
A2 = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/face-plates/A2_Front_plate.png")
CONFIG = ROOT / "config/validation.yaml"
SETTINGS = ROOT / "config/settings.yaml"
WARDROBE = ROOT / "config/projects/linh_an/wardrobe_index.json"
WESTLAKE = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/Westlake-railing-street.jpg")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def member(role: str, reference_id: str | None, path: Path | None, source: str | None, version: str | None, status: str) -> dict:
    return {"role": role, "reference_id": reference_id, "path": str(path) if path else None, "sha256": sha(path) if path and path.is_file() else None, "authority_source": source, "version": version, "status": status}


def main() -> None:
    base_sha, candidate_sha, a2_sha = sha(BASE), sha(COMPOSITE), sha(A2)
    assert base_sha == "bb031e7adfcc0c7d79544c3edb932eebafc1f797a59881415e57addc584d26a0"
    assert candidate_sha == "cc78e635e73e8656b82cd808af0ae837ca88c275f180b3289407dcc9545cd6f0"
    assert a2_sha == "1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d"

    refs = [
        member("identity", "A2_FRONT", A2, "existing A2 authority lock", "sha256-lock-v1", "FOUND_AUTHORITATIVE"),
        member("action_pose", None, None, None, None, "UNRESOLVED"),
        member("outfit", None, None, str(WARDROBE), None, "UNRESOLVED"),
        member("environment", "westlake_railing_street", WESTLAKE, "config/projects/venho_hotel/subjects/westlake.nguyen_dinh_thi_street_2026.overrides.yaml", "source-note-v1", "FOUND_AUTHORITATIVE" if WESTLAKE.exists() else "UNRESOLVED"),
        member("composition", "locked_action_01_jogging", BASE, "locked base SHA authority", "sha256-lock-v1", "FOUND_AUTHORITATIVE"),
    ]
    unresolved = [item["role"] for item in refs if item["status"] != "FOUND_AUTHORITATIVE"]
    report = {
        "task": "GW-P0-T2-QC4H1",
        "authority": {"project": "venho_linh_an", "image_dna_subject": "linh_an_action_composite", "scenario_profile": "outdoor_action_jogging_west_lake", "authority_origin": "HUMAN_APPROVED_RECOVERY"},
        "reference_set": {"id": "linh_an_action_composite_global_v1", "version": "1.0", "references": refs, "unresolved_roles": unresolved, "sha256": None, "materialized": False},
        "validator_binding": {"provider": "gemini", "model": "gemini-flash-latest", "samples": 1, "config_source": str(CONFIG), "config_sha256": sha(CONFIG), "provider_model_source": str(SETTINGS), "provider_model_config_sha256": sha(SETTINGS)},
        "manifest": {"path": None, "sha256": None, "base_sha256": base_sha, "candidate_sha256": candidate_sha},
        "future_provenance": {"persistence_patch_applied": True, "schema_fields": ["project", "image_dna_subject", "scenario_profile_id", "reference_set_id", "reference_set_version", "reference_set_sha256", "validation_config_sha256", "authority_origin"], "missing_context_fails_closed": True},
        "execution": {"validator_called": "NO", "comfyui_rerun": "NO", "image_regenerated": "NO", "thresholds_changed": "NO", "canonical_artifacts_unchanged": True},
        "final": {"status": "BLOCKED", "ready_for_qc4i": "NO", "reason": "approved semantic bindings exist, but required authoritative action_pose and outfit artifacts are unresolved", "human_authority_required": ["action_pose reference artifact/record", "mint-green outfit reference artifact/record"]},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"task": report["task"], "status": report["final"]["status"], "unresolved_roles": unresolved, "report": str(OUT), "validator_called": "NO"}, indent=2))


if __name__ == "__main__":
    main()
