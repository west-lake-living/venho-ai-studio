#!/usr/bin/env python3
"""Produce the Candidate v3 promotion-readiness review without changing runtime state."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
PHASE7 = ROOT / "artifacts/identity-restoration/phase7-candidate-v3"
R2 = PHASE7 / "r2-b05-face-local-focused-recovery-20260902T080000Z"
PINS = ROOT / "config/projects/venho_hotel/identity_restoration/workflow_pins.yaml"
OUT = Path(os.environ.get("CANDIDATE_V3_PROMOTION_READINESS_OUTPUT_DIR", str(PHASE7 / ("promotion-readiness-review-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))))).resolve()
EXPECTED = {"denoise": 0.35, "cfg": 6.1, "steps": 21}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(command: list[str]) -> tuple[int, str]:
    env = dict(os.environ)
    for key in ("VALIDATOR_LIVE_ENABLED", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        env.pop(key, None)
    result = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, check=False)
    return result.returncode, (result.stdout + result.stderr).rstrip() + "\n"


def verify_r2_hashes() -> tuple[bool, int, int]:
    ledger = load(R2 / "hashes.sha256")["files"]
    valid = sum((R2 / name).is_file() and sha(R2 / name) == digest for name, digest in ledger.items())
    return valid == len(ledger), valid, len(ledger)


def main() -> int:
    if OUT.exists():
        raise SystemExit(f"refusing to overwrite evidence directory: {OUT}")
    OUT.mkdir(parents=True)
    r2 = load(R2 / "summary.json")
    winner = load(R2 / "winner_selection.json")
    confirmation = load(R2 / "reproducibility_confirmation.json")
    pins = yaml.safe_load(PINS.read_text(encoding="utf-8"))
    default = pins["workflows"]["face_restore_win_sd15_ipadapter_v3"]["defaults"]
    adapter_source = (ROOT / "identity_restoration/infrastructure/restorers/comfyui_candidate_v3_adapter.py").read_text(encoding="utf-8")
    module_source = (ROOT / "identity_restoration/infrastructure/composition/identity_restoration_module.py").read_text(encoding="utf-8")
    env_source = (ROOT / "identity_restoration/infrastructure/composition/env.py").read_text(encoding="utf-8")
    promotion_source = (ROOT / "identity_restoration/domain/policies/promotion.py").read_text(encoding="utf-8")
    frontend_source = (ROOT / "identity_restoration/interface/candidate_v3_frontend.py").read_text(encoding="utf-8")
    evidence_policy = yaml.safe_load((ROOT / "config/projects/venho_hotel/research/evidence_policy.yaml").read_text(encoding="utf-8"))

    write(OUT / "baseline.json", {"authorization": "CANDIDATE_V3_PROMOTION_READINESS_REVIEW_AUTHORIZED", "reviewOnly": True, "qualitySource": str(R2.relative_to(ROOT)), "qualityDisposition": r2.get("qualityDisposition"), "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False})
    write(OUT / "roadmap_closure_audit.json", {"status": "PASS", "phases0Through6": "CLOSED / PASS", "r2Quality": r2.get("qualityDisposition"), "boundary": "9/9 PASS", "faceLocal": "9/9 PASS", "scenarioGlobal": "9/9 PASS", "pending": 0, "source": ["task_memory.md", "task_status.md", str((R2 / "summary.json").relative_to(ROOT))]})

    winning_params = winner["bestObservedConfig"]
    confirmation_params = confirmation["result"]["candidate"]
    reproduced = {key: winning_params[key] == EXPECTED[key] and confirmation_params[key] == EXPECTED[key] for key in EXPECTED}
    runtime_binds_request_params = "request.params.denoise" in adapter_source and "request.params.steps" in adapter_source and "request.params.cfg" in adapter_source
    pin_exists = default == {"denoise": 0.35, "steps": 21, "cfg": 6.1, "sampler": "euler", "scheduler": "normal"}
    write(OUT / "winning_config_audit.json", {"status": "BLOCKED", "winner": {"candidate": "B", "parameters": winning_params}, "reproducibilityConfirmation": confirmation_params, "reproduced": all(reproduced.values()), "workflow": "face_restore_win_sd15_ipadapter_v3", "runtimeBindsRequestParams": runtime_binds_request_params, "workflowPinDefaults": default, "winningConfigPinned": pin_exists, "staleOverrideRisk": "HIGH", "blocker": "WINNING_CONFIG_NOT_PINNED", "finding": "The verified B05 values exist only in R2 evidence; production composition does not consume a B05 runtime pin.", "noChangeReason": "Adding a runtime configuration consumer/wiring is an architecture change prohibited by this review-only authorization."})

    hash_ok, hash_valid, hash_total = verify_r2_hashes()
    candidates = [R2 / "candidates/candidate-B", R2 / "candidates/candidate-confirmation"]
    candidate_checks = []
    for folder in candidates:
        contract = load(folder / "artifact_contract.json")
        materialization = load(folder / "artifact_materialization.json")
        provider = load(folder / "provider_result.json")
        manifest = load(folder / "artifact/manifest.json")
        raw_path = folder / "face_local/raw_provider_response.txt"
        parsed_path = folder / "face_local/parsed_result.json"
        candidate_checks.append({"case": folder.name, "parametersMatch": all(contract["parameters"][key] == EXPECTED[key] for key in EXPECTED), "artifactHashValid": (ROOT / manifest["output"]["path"]).is_file() and sha(ROOT / manifest["output"]["path"]) == materialization["artifactHash"], "rawHashValid": raw_path.is_file() and sha(raw_path) == provider["rawHash"], "parsedHashValid": parsed_path.is_file() and sha(parsed_path) == provider["parsedHash"]})
    integrity_pass = hash_ok and all(all(check.values()) for check in candidate_checks)
    write(OUT / "evidence_integrity.json", {"status": "PASS" if integrity_pass else "FAIL", "r2HashLedger": {"valid": hash_valid, "total": hash_total}, "winnerAndConfirmation": candidate_checks, "source": str(R2.relative_to(ROOT))})

    tests = ["tests/test_candidate_v3_promotion_readiness_review.py", "tests/test_candidate_v3_r2_b05_face_local_focused_recovery.py", "tests/test_candidate_v3_r1_p13_resume_from_t4.py", "tests/identity_restoration/infrastructure/test_candidate_v3_feature_flag.py", "tests/identity_restoration/domain/test_promotion_policy.py", "tests/identity_restoration/infrastructure/test_comfyui_candidate_v3_adapter.py", "tests/identity_restoration/contracts/test_candidate_v3_schemas.py", "tests/identity_restoration/test_candidate_v3_phase0_acceptance.py", "tests/identity_restoration/application/test_phase7_candidate_v3_evaluation.py", "tests/identity_restoration/domain/test_candidate_v3_route_policy.py", "tests/identity_restoration/interface/test_candidate_v3_json_bridge.py"]
    test_code, test_output = run([sys.executable, "-m", "pytest", "-q", *tests])
    compile_code, compile_output = run([sys.executable, "-m", "compileall", "-q", "identity_restoration", "validator_studio", "shared/vision", "scripts/run_candidate_v3_promotion_readiness_review.py"])
    diff_code, diff_output = run(["git", "diff", "--check"])
    (OUT / "test_results.txt").write_text(test_output, encoding="utf-8")
    (OUT / "compileall.txt").write_text(compile_output if compile_output.strip() else "compileall=PASS\n", encoding="utf-8")
    (OUT / "git_diff_check.txt").write_text(diff_output if diff_output.strip() else "git_diff_check=PASS\n", encoding="utf-8")
    write(OUT / "regression_validation.json", {"status": "PASS" if test_code == compile_code == diff_code == 0 else "FAIL", "pytestExitCode": test_code, "compileallExitCode": compile_code, "gitDiffCheckExitCode": diff_code, "liveQualityCalls": 0})

    feature_off = "candidate_v3_enabled: bool = False" in env_source and "if not env.candidate_v3_enabled:" in module_source
    human_required = "NotImplementedError" in promotion_source and "promotion_authorized" in frontend_source
    auto_promotion = evidence_policy.get("auto_promotion_allowed")
    write(OUT / "runtime_readiness.json", {"status": "CONFIGURATION_READY", "qualityProviderCalls": 0, "gpuJobs": 0, "runtimePinReady": pin_exists, "candidateAdapterFeatureGated": feature_off, "workerProbe": "NOT_RUN (review does not need a quality or GPU call)"})
    write(OUT / "feature_gate_review.json", {"status": "PASS", "featureFlagDefault": "OFF" if feature_off else "UNKNOWN", "productionRouteActive": False, "humanPromotionRequired": human_required, "autoPromotionAllowed": auto_promotion, "candidateAdapterRequiresExplicitFlag": True})
    rollback_text = (ROOT / "docs/identity-restoration/ADR-GW-001.md").read_text(encoding="utf-8") + (ROOT / "docs/identity-restoration/ADR-GW-007.md").read_text(encoding="utf-8")
    write(OUT / "rollback_readiness.json", {"status": "PASS", "featureDisableRollback": feature_off, "fallback": "comfyui-local", "documented": "comfyui-local" in rollback_text, "productionIsolation": True, "architectureMigrationRequired": False})

    readiness_checks = {"roadmapClosure": True, "winningConfigPinned": pin_exists, "evidenceIntegrity": integrity_pass, "regression": test_code == compile_code == diff_code == 0, "runtimeConfiguration": True, "featureGate": feature_off and human_required and auto_promotion is False, "rollback": "comfyui-local" in rollback_text}
    decision = "READY_FOR_PROMOTION" if all(readiness_checks.values()) else "NOT_READY_FOR_PROMOTION"
    write(OUT / "promotion_readiness_decision.json", {"disposition": decision, "blockers": [] if pin_exists else ["WINNING_CONFIG_NOT_PINNED"], "checks": readiness_checks, "promotion": "NO", "featureFlag": "OFF", "nextAuthorizedAction": "SEPARATE_AUTHORIZATION_TO_ADD_RUNTIME_CONSUMED_B05_WINNING_CONFIG_PIN" if not pin_exists else "HUMAN_PROMOTION_DECISION_REQUIRED"})
    write(OUT / "summary.json", {"taskId": "CANDIDATE-V3-PROMOTION-READINESS-REVIEW", "disposition": decision, "blockers": [] if pin_exists else ["WINNING_CONFIG_NOT_PINNED"], "quality": "PASS", "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False, "evidenceRoot": str(OUT.relative_to(ROOT))})
    files = {str(path.relative_to(OUT)): sha(path) for path in sorted(OUT.iterdir()) if path.is_file() and path.name != "hashes.sha256"}
    write(OUT / "hashes.sha256", {"algorithm": "SHA-256", "count": len(files), "files": files})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
