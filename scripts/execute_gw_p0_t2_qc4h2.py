"""Materialize the human-approved global validation authority binding."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEARCH = ROOT / "data/identity_restoration_runs/gw-p0-t2-qc4e-local-search"
OUT = SEARCH / "qc4h2/global-validation-authority.json"
BASE = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/action-composite-live/action_01_jogging.png")
COMPOSITE = SEARCH / "qc4e-w070-d060/composite/image.png"
RESTORED = SEARCH / "qc4e-w070-d060/artifacts/restored_crop.png"
MASK = ROOT / "data/identity_restoration_runs/gw-p0-t2-qc4c2f-local-candidate/diagnostics/geometry_preserving_mask.png"
A2 = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/face-plates/A2_Front_plate.png")
ENV = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/Westlake-railing-street.jpg")
CONFIG = ROOT / "config/validation.yaml"
SETTINGS = ROOT / "config/settings.yaml"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    expected = {
        "base": "bb031e7adfcc0c7d79544c3edb932eebafc1f797a59881415e57addc584d26a0",
        "candidate": "cc78e635e73e8656b82cd808af0ae837ca88c275f180b3289407dcc9545cd6f0",
        "restored": "fa2b0007c1a8bd336fb17d6903b38758f45b193ee8c78aed9e41f9f33a1be155",
        "mask": "ea7f63bfc72cb8723cfdb480ab45d56917a83aa93ba4cff58441bf56f0d644e2",
        "a2": "1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d",
    }
    actual = {"base": sha(BASE), "candidate": sha(COMPOSITE), "restored": sha(RESTORED), "mask": sha(MASK), "a2": sha(A2)}
    assert actual == expected, actual
    members = [
        {"role": "identity", "reference_id": "A2_FRONT", "path": str(A2), "sha256": actual["a2"], "authority_origin": "EXISTING_A2_AUTHORITY", "stage": "identity"},
        {"role": "action_pose", "reference_id": "locked_action_01_jogging", "path": str(BASE), "sha256": actual["base"], "authority_origin": "HUMAN_APPROVED_RECOVERY", "stage": "post_identity_restoration", "semantic": "preserve_source_action_pose"},
        {"role": "outfit", "reference_id": "locked_action_01_jogging", "path": str(BASE), "sha256": actual["base"], "authority_origin": "HUMAN_APPROVED_RECOVERY", "stage": "post_identity_restoration", "semantic": "preserve_source_outfit"},
        {"role": "environment", "reference_id": "westlake_railing_street", "path": str(ENV), "sha256": sha(ENV), "authority_origin": "EXISTING_WESTLAKE_REFERENCE", "stage": "global_composite"},
        {"role": "composition", "reference_id": "locked_action_01_jogging", "path": str(BASE), "sha256": actual["base"], "authority_origin": "HUMAN_APPROVED_RECOVERY", "stage": "post_identity_restoration"},
    ]
    ref_set_payload = {"id": "linh_an_action_composite_global_v1", "version": "1.0", "members": members}
    ref_set_sha = hashlib.sha256(json.dumps(ref_set_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    record = {
        "task": "GW-P0-T2-QC4H2",
        "authority_origin": "HUMAN_APPROVED_RECOVERY",
        "project": "venho_linh_an",
        "image_dna_subject": "linh_an_action_composite",
        "scenario_profile": "outdoor_action_jogging_west_lake",
        "reference_set": {**ref_set_payload, "sha256": ref_set_sha, "unresolved_roles": [], "complete": True},
        "validator_binding": {"provider": "gemini", "model": "gemini-flash-latest", "samples": 1, "validation_config": str(CONFIG), "validation_config_sha256": sha(CONFIG), "provider_model_config": str(SETTINGS), "provider_model_config_sha256": sha(SETTINGS)},
        "artifacts": {"base_sha256": actual["base"], "candidate_sha256": actual["candidate"], "restored_sha256": actual["restored"], "mask_sha256": actual["mask"]},
        "semantic_role_separation": {"identity": "A2_FRONT", "action_pose": "locked base", "outfit": "locked base", "environment": "Westlake-railing-street.jpg", "composition": "locked base"},
        "execution": {"validator_called": "NO", "comfyui_rerun": "NO", "image_regenerated": "NO", "thresholds_changed": "NO", "canonical_artifacts_unchanged": True},
        "manifest": {"semantic_context_complete": True, "authority_is_historical_generation_provenance": False},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"task": record["task"], "status": "PASS", "reference_set_sha256": ref_set_sha, "manifest": str(OUT), "validator_called": "NO"}, indent=2))


if __name__ == "__main__":
    main()
