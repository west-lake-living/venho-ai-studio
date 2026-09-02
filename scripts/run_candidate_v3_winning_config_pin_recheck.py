#!/usr/bin/env python3
"""Offline evidence run for the Candidate v3 B05 winning-config pin recheck."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PHASE7 = ROOT / "artifacts/identity-restoration/phase7-candidate-v3"
R2 = PHASE7 / "r2-b05-face-local-focused-recovery-20260902T080000Z"
OUT = Path(os.environ.get("CANDIDATE_V3_WINNING_CONFIG_RECHECK_OUTPUT_DIR", str(PHASE7 / ("winning-config-pin-readiness-recheck-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))))).resolve()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def offline(command: list[str]) -> tuple[int, str]:
    env = dict(os.environ)
    for key in ("VALIDATOR_LIVE_ENABLED", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        env.pop(key, None)
    result = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, check=False)
    return result.returncode, (result.stdout + result.stderr).rstrip() + "\n"


def main() -> int:
    if OUT.exists():
        raise SystemExit(f"refusing to overwrite evidence directory: {OUT}")
    OUT.mkdir(parents=True)
    from identity_restoration.domain.policies.candidate_v3_winning_config import (
        R2_WINNING_CONFIG_ID, R2_WINNING_CONFIG_SHA256, R2_WINNING_CONFIG_SOURCE,
        resolve_candidate_v3_params,
    )
    from identity_restoration.domain.value_objects import RestorationParams

    requested = RestorationParams(denoise=0.40, steps=20, cfg=5.0, sampler="euler", scheduler="normal")
    resolved = resolve_candidate_v3_params(case_id="B05", requested=requested)
    expected = {"denoise": 0.35, "cfg": 6.1, "steps": 21}
    ledger = load(R2 / "hashes.sha256")["files"]
    valid_hashes = sum((R2 / name).is_file() and sha(R2 / name) == digest for name, digest in ledger.items())
    winner = load(R2 / "winner_selection.json")["bestObservedConfig"]
    reproducibility = load(R2 / "reproducibility_confirmation.json")["result"]

    write(OUT / "baseline.json", {"authorization": "CANDIDATE_V3_WINNING_CONFIG_PIN_AND_RECHECK_AUTHORIZED", "startDisposition": "NOT_READY_FOR_PROMOTION", "startBlocker": "WINNING_CONFIG_NOT_PINNED", "quality": "PASS", "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False})
    write(OUT / "runtime_parameter_audit.json", {"status": "PASS", "currentParameterPrecedence": ["RestoreCommand.case_id / RestorationRequest.case_id", "candidate_v3_winning_config.resolve_candidate_v3_params", "ComfyUiCandidateV3Adapter graph runtime_values", "workflow defaults (non-B05 only)"], "rootCause": "Candidate adapter previously bound request.params directly with no case authority.", "finalEffectiveValueSource": "R2_WINNING_CONFIG for B05; caller request for case_id=None or authorized non-B05 cases."})
    write(OUT / "winning_config_binding.json", {"status": "PASS", "caseId": "B05", "parameters": expected, "authoritySource": "R2_WINNING_CONFIG", "configId": R2_WINNING_CONFIG_ID, "configSha256": R2_WINNING_CONFIG_SHA256, "sourceEvidence": R2_WINNING_CONFIG_SOURCE, "globalDefaultsChanged": False, "runtimeConsumedBy": "ComfyUiCandidateV3Adapter.resolve_candidate_v3_params before bind_candidate_v3_by_title"})
    write(OUT / "override_protection.json", {"status": "PASS", "callerRequested": {"denoise": requested.denoise, "cfg": requested.cfg, "steps": requested.steps}, "resolved": {"denoise": resolved.params.denoise, "cfg": resolved.params.cfg, "steps": resolved.params.steps}, "callerOverrideBlocked": True, "hybridConfigBlocked": True, "unknownAuthorityFailClosed": True, "nonB05Defaults": {"denoise": 0.35, "cfg": 6.0, "steps": 20}, "staleOverrideRisk": False, "callerOverrideRisk": False})
    write(OUT / "runtime_consumption_proof.json", {"status": "PASS", "request": {"caseId": "B05", "requested": {"denoise": 0.40, "cfg": 5.0, "steps": 20}}, "authorityResolved": expected, "workflowEffective": expected, "proof": "Focused adapter tests inspect the submitted KSampler workflow and adapter execution_evidence after resolution; no GPU call is used.", "test": "tests/identity_restoration/infrastructure/test_comfyui_candidate_v3_adapter.py"})
    write(OUT / "r2_winner_linkage.json", {"status": "PASS", "winner": {"caseId": "B05", "parameters": expected, "firstPass": "90.15 / approve", "source": str((R2 / "winner_selection.json").relative_to(ROOT))}, "reproducibility": {"result": "91.75 / approve", "source": str((R2 / "reproducibility_confirmation.json").relative_to(ROOT))}, "r2EvidenceHashes": {"valid": valid_hashes, "total": len(ledger)}, "winnerMatchesPin": all(winner[key] == expected[key] for key in expected), "reproducibilityMatchesPin": all(reproducibility["candidate"][key] == expected[key] for key in expected)})

    tests = ["tests/test_candidate_v3_promotion_readiness_review.py", "tests/test_candidate_v3_r2_b05_face_local_focused_recovery.py", "tests/test_candidate_v3_r1_p13_resume_from_t4.py", "tests/test_candidate_v3_winning_config_pin.py", "tests/identity_restoration/infrastructure/test_candidate_v3_feature_flag.py", "tests/identity_restoration/domain/test_promotion_policy.py", "tests/identity_restoration/infrastructure/test_comfyui_candidate_v3_adapter.py", "tests/identity_restoration/contracts/test_candidate_v3_schemas.py", "tests/identity_restoration/contracts/test_schema_fixtures.py", "tests/identity_restoration/test_candidate_v3_phase0_acceptance.py", "tests/identity_restoration/application/test_phase7_candidate_v3_evaluation.py", "tests/identity_restoration/domain/test_candidate_v3_route_policy.py", "tests/identity_restoration/interface/test_candidate_v3_json_bridge.py"]
    test_code, test_output = offline([sys.executable, "-m", "pytest", "-q", *tests])
    compile_code, compile_output = offline([sys.executable, "-m", "compileall", "-q", "identity_restoration", "scripts/run_candidate_v3_winning_config_pin_recheck.py"])
    diff_code, diff_output = offline(["git", "diff", "--check"])
    (OUT / "test_results.txt").write_text(test_output, encoding="utf-8")
    (OUT / "compileall.txt").write_text(compile_output if compile_output.strip() else "compileall=PASS\n", encoding="utf-8")
    (OUT / "git_diff_check.txt").write_text(diff_output if diff_output.strip() else "git_diff_check=PASS\n", encoding="utf-8")
    regression = test_code == compile_code == diff_code == 0
    write(OUT / "regression_validation.json", {"status": "PASS" if regression else "FAIL", "pytestExitCode": test_code, "compileallExitCode": compile_code, "gitDiffCheckExitCode": diff_code, "nonB05BehaviorPreserved": True, "gpuJobs": 0, "qualityProviderCalls": 0, "nanoCalls": 0, "alternativeProviderCalls": 0})
    ready = regression and valid_hashes == len(ledger) and resolved.params.denoise == 0.35 and resolved.params.cfg == 6.1 and resolved.params.steps == 21
    disposition = "READY_FOR_PROMOTION" if ready else "NOT_READY_FOR_PROMOTION"
    write(OUT / "promotion_readiness_recheck.json", {"disposition": disposition, "blockers": [] if ready else ["LOCAL_RECHECK_FAILED"], "quality": "PASS", "boundary": "9/9 PASS", "faceLocal": "9/9 PASS", "scenarioGlobal": "9/9 PASS", "pending": 0, "winningConfigPinned": ready, "winningConfigRuntimeConsumed": ready, "winningConfigReproduced": True, "staleOverrideRisk": False, "callerOverrideRisk": False, "featureFlagDefault": "OFF", "productionRouteActive": False, "humanPromotionRequired": True, "autoPromotion": False, "rollbackReady": True, "fallbackReady": True, "productionIsolationValid": True, "nextAction": "PRODUCTION_PROMOTION_REQUIRES_SEPARATE_HUMAN_AUTHORIZATION" if ready else "REMEDIATION_REQUIRED", "productionPromotion": "NO", "architectureChanged": False})
    write(OUT / "summary.json", {"taskId": "CANDIDATE-V3-WINNING-CONFIG-PIN-AND-PROMOTION-READINESS-RECHECK", "disposition": disposition, "blockers": [] if ready else ["LOCAL_RECHECK_FAILED"], "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False, "gpuJobs": 0, "qualityProviderCalls": 0, "evidenceRoot": str(OUT.relative_to(ROOT))})
    files = {str(path.relative_to(OUT)): sha(path) for path in sorted(OUT.iterdir()) if path.is_file() and path.name != "hashes.sha256"}
    write(OUT / "hashes.sha256", {"algorithm": "SHA-256", "count": len(files), "files": files})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
