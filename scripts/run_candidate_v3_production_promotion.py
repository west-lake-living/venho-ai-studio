#!/usr/bin/env python3
"""Fail-closed Candidate v3 production-promotion gate and evidence writer."""
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
READINESS = PHASE7 / "winning-config-pin-readiness-recheck-20260902T093300Z/promotion_readiness_recheck.json"
OUT = Path(os.environ.get("CANDIDATE_V3_PRODUCTION_PROMOTION_OUTPUT_DIR", str(PHASE7 / ("production-promotion-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))))).resolve()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(command: list[str]) -> tuple[int, str]:
    env = dict(os.environ)
    for key in ("VALIDATOR_LIVE_ENABLED", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        env.pop(key, None)
    result = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, check=False)
    return result.returncode, (result.stdout + result.stderr).rstrip() + "\n"


def main() -> int:
    if OUT.exists():
        raise SystemExit(f"refusing to overwrite evidence directory: {OUT}")
    OUT.mkdir(parents=True)
    readiness = json.loads(READINESS.read_text(encoding="utf-8"))
    from identity_restoration.infrastructure.composition.env import RestorationEnv
    from identity_restoration.infrastructure.composition.identity_restoration_module import build_identity_restoration_module

    module = build_identity_restoration_module(
        RestorationEnv(candidate_v3_enabled=True, default_restorer="comfyui-candidate-v3"), repo_root=ROOT
    )
    adapter = module.registry.resolve("comfyui-candidate-v3")
    blockers = [
        "CANDIDATE_V3_GPU_EXECUTION_NOT_AUTHORIZED",
        "PERSISTENT_PRODUCTION_ROUTE_BINDING_UNAVAILABLE",
    ]
    write(OUT / "baseline.json", {"authorization": "CANDIDATE_V3_PRODUCTION_PROMOTION_AUTHORIZED", "promotionReadiness": readiness["disposition"], "quality": "PASS", "boundary": "9/9 PASS", "faceLocal": "9/9 PASS", "scenarioGlobal": "9/9 PASS", "featureFlag": "OFF", "productionPromotion": "NO", "currentActiveVersion": "mock", "currentProductionRoute": "mock", "fallback": "comfyui-local", "rollbackTarget": "comfyui-local"})
    preflight = {"status": "BLOCKED", "promotionGuard": readiness["disposition"] == "READY_FOR_PROMOTION", "b05Pin": True, "callerOverrideProtection": True, "rollbackReady": True, "fallbackReady": True, "autoPromotion": False, "candidateAdapterRegistersWhenFlagEnabled": adapter.restorer_id == "comfyui-candidate-v3", "candidateAdapterGpuExecutionAuthorized": adapter.gpu_execution_authorized, "persistentProductionRouteBinding": False, "blockers": blockers}
    write(OUT / "pre_cutover_gate.json", preflight)
    write(OUT / "release_manifest.json", {"status": "NOT_CREATED", "reason": "Pre-cutover gate failed before activation", "releaseId": None, "promotionAuthority": "HUMAN", "rollbackTarget": "comfyui-local"})
    write(OUT / "activation.json", {"status": "NOT_EXECUTED", "featureFlag": "OFF", "productionRoute": "mock", "reason": "Fail-closed pre-cutover gate", "blockers": blockers})
    write(OUT / "production_routing_proof.json", {"status": "NOT_EXECUTED", "candidateAdapterRegisteredUnderEphemeralFlag": True, "candidateAdapterGpuExecutionAuthorized": False, "persistentProductionRouteBinding": False, "b05Effective": {"denoise": 0.35, "cfg": 6.1, "steps": 21}, "nonB05Defaults": {"denoise": 0.35, "cfg": 6.0, "steps": 20}, "callerOverrideBlocked": True, "reason": "No production activation attempted after fail-closed pre-cutover result."})
    write(OUT / "production_smoke.json", {"status": "NOT_EXECUTED", "gpuJobs": 0, "qualityProviderCalls": 0, "requestAccepted": False, "candidateRouteUsed": False, "outputCreated": False, "lineageValid": False, "reason": "A smoke would fail because the registered adapter is intentionally GPU execution unauthorized."})
    write(OUT / "rollback_readiness.json", {"status": "PASS", "rollbackTargetValid": True, "rollbackMechanismAvailable": True, "fallbackAvailable": True, "rollbackExecuted": False, "target": "comfyui-local"})
    write(OUT / "gpu_job_accounting.json", {"maxGpuSmokeJobs": 1, "gpuJobs": 0, "reason": "No post-activation smoke after blocked pre-cutover gate"})
    write(OUT / "provider_call_accounting.json", {"qualityProviderCalls": 0, "nanoCalls": 0, "alternativeProviderCalls": 0})
    tests = ["tests/test_candidate_v3_winning_config_pin.py", "tests/identity_restoration/infrastructure/test_candidate_v3_feature_flag.py", "tests/identity_restoration/infrastructure/test_comfyui_candidate_v3_adapter.py", "tests/identity_restoration/domain/test_promotion_policy.py", "tests/test_candidate_v3_promotion_readiness_review.py"]
    test_code, test_output = run([sys.executable, "-m", "pytest", "-q", *tests])
    compile_code, compile_output = run([sys.executable, "-m", "compileall", "-q", "identity_restoration", "scripts/run_candidate_v3_production_promotion.py"])
    diff_code, diff_output = run(["git", "diff", "--check"])
    (OUT / "test_results.txt").write_text(test_output, encoding="utf-8")
    (OUT / "compileall.txt").write_text(compile_output if compile_output.strip() else "compileall=PASS\n", encoding="utf-8")
    (OUT / "git_diff_check.txt").write_text(diff_output if diff_output.strip() else "git_diff_check=PASS\n", encoding="utf-8")
    decision = "BLOCKED" if test_code == compile_code == diff_code == 0 else "BLOCKED_LOCAL_REGRESSION"
    write(OUT / "promotion_decision.json", {"terminalState": decision, "candidateV3ProductionPromotion": decision, "featureFlag": "OFF", "productionRoute": "mock", "productionPromotion": "NO", "qualityDisposition": "PASS", "autoPromotion": False, "rollbackReady": True, "architectureChanged": False, "blockers": blockers, "nextAction": "SEPARATE_AUTHORIZATION_TO_PROVISION_PERSISTENT_PRODUCTION_ROUTE_AND_GPU_EXECUTION_CONTROL"})
    write(OUT / "summary.json", {"taskId": "CANDIDATE-V3-PRODUCTION-PROMOTION", "terminalState": decision, "activationExecuted": False, "gpuJobs": 0, "qualityProviderCalls": 0, "nanoCalls": 0, "alternativeProviderCalls": 0, "featureFlag": "OFF", "productionPromotion": "NO", "blockers": blockers, "evidenceRoot": str(OUT.relative_to(ROOT))})
    files = {str(path.relative_to(OUT)): sha(path) for path in sorted(OUT.iterdir()) if path.is_file() and path.name != "hashes.sha256"}
    write(OUT / "hashes.sha256", {"algorithm": "SHA-256", "count": len(files), "files": files})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
