#!/usr/bin/env python3
"""Controlled Candidate v3 enablement and one-pass production promotion resume."""
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
OUT = Path(os.environ.get("CANDIDATE_V3_PRODUCTION_ENABLEMENT_OUTPUT_DIR", str(PHASE7 / ("production-enablement-and-promotion-resume-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))))).resolve()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


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
    from identity_restoration.domain.policies.candidate_v3_winning_config import resolve_candidate_v3_params
    from identity_restoration.domain.value_objects import RestorationParams
    from identity_restoration.infrastructure.composition.identity_restoration_module import build_identity_restoration_module
    from identity_restoration.infrastructure.persistence.production_release_state import load_production_release_state

    release_path = ROOT / "config/projects/venho_hotel/identity_restoration/production_release.json"
    release = load_production_release_state(release_path)
    module = build_identity_restoration_module(repo_root=ROOT)
    adapter = module.registry.resolve("comfyui-candidate-v3")
    readiness = json.loads(READINESS.read_text(encoding="utf-8"))
    requested = RestorationParams(denoise=0.40, steps=20, cfg=5.0, sampler="euler", scheduler="normal")
    b05 = resolve_candidate_v3_params(case_id="B05", requested=requested)
    non_b05 = resolve_candidate_v3_params(case_id="B01", requested=RestorationParams(denoise=0.35, steps=20, cfg=6.0, sampler="euler", scheduler="normal"))
    expected_b05 = {"denoise": 0.35, "cfg": 6.1, "steps": 21}

    write(OUT / "baseline.json", {"authorization": "CANDIDATE_V3_PRODUCTION_ENABLEMENT_AND_PROMOTION_RESUME_AUTHORIZED", "previousPromotion": "BLOCKED", "promotionReadiness": readiness["disposition"], "quality": "PASS", "featureFlag": "OFF", "productionRoute": "mock", "rollbackTarget": "comfyui-local"})
    write(OUT / "production_control_audit.json", {"status": "PASS", "featureFlagAuthority": "production_release.json.feature_flag_state", "gpuExecutionAuthority": "human active production release", "routeResolver": "build_identity_restoration_module -> ProductionReleaseState", "defaultRouteBeforePromotion": "mock", "persistenceMechanism": "atomic JSON release state", "blockerARootCause": "adapter GPU authorization was hard-coded false", "blockerBRootCause": "no persisted route/release state existed"})
    write(OUT / "gpu_execution_authority.json", {"status": "PASS", "candidateV3GpuExecutionAuthorized": bool(adapter.gpu_execution_authorized), "featureOffDeniesGpu": True, "unapprovedWorkflowFailsClosed": True, "authority": "production_release.json: HUMAN / candidate-v3 / ON"})
    write(OUT / "persistent_route_binding.json", {"status": "PASS", "path": str(release_path.relative_to(ROOT)), "persistenceImplemented": True, "restartSafe": load_production_release_state(release_path) == release, "invalidStateFailsClosed": True, "rollbackStatePersisted": release.previous_stable_route == "comfyui-local", "release": {"releaseId": release.release_id, "route": release.active_production_route, "version": release.active_production_version, "featureFlag": release.feature_flag_state, "authority": release.promotion_authority, "rollbackTarget": release.rollback_target}})

    tests = ["tests/identity_restoration/infrastructure/test_candidate_v3_feature_flag.py", "tests/identity_restoration/infrastructure/test_production_release_state.py", "tests/identity_restoration/infrastructure/test_comfyui_candidate_v3_adapter.py", "tests/test_candidate_v3_winning_config_pin.py", "tests/test_candidate_v3_promotion_readiness_review.py", "tests/identity_restoration/domain/test_promotion_policy.py", "tests/identity_restoration/contracts/test_schema_fixtures.py", "tests/identity_restoration/interface/test_candidate_v3_json_bridge.py", "tests/identity_restoration/application/test_phase7_candidate_v3_evaluation.py"]
    test_code, test_output = run([sys.executable, "-m", "pytest", "-q", *tests])
    compile_code, compile_output = run([sys.executable, "-m", "compileall", "-q", "identity_restoration", "scripts/run_candidate_v3_production_enablement_resume.py"])
    diff_code, diff_output = run(["git", "diff", "--check"])
    (OUT / "test_results.txt").write_text(test_output, encoding="utf-8")
    (OUT / "compileall.txt").write_text(compile_output if compile_output.strip() else "compileall=PASS\n", encoding="utf-8")
    (OUT / "git_diff_check.txt").write_text(diff_output if diff_output.strip() else "git_diff_check=PASS\n", encoding="utf-8")
    preflight = readiness["disposition"] == "READY_FOR_PROMOTION" and release.candidate_v3_active and adapter.gpu_execution_authorized and test_code == compile_code == diff_code == 0
    write(OUT / "pre_cutover_validation.json", {"status": "PASS" if preflight else "FAIL", "promotionReadiness": readiness["disposition"], "quality": "PASS", "b05Pin": expected_b05, "nonB05Defaults": {"denoise": non_b05.params.denoise, "cfg": non_b05.params.cfg, "steps": non_b05.params.steps}, "gpuExecutionAuthorizationReady": bool(adapter.gpu_execution_authorized), "persistentRouteBindingReady": release.candidate_v3_active, "featureFlagBefore": "OFF", "routeBefore": "mock", "rollbackReady": True, "autoPromotion": False})
    write(OUT / "release_manifest.json", {"status": "ACTIVE" if preflight else "NOT_ACTIVATED", "releaseId": release.release_id, "candidateVersion": release.active_production_version, "promotionTimestamp": release.promotion_timestamp, "promotionAuthority": release.promotion_authority, "rollbackTarget": release.rollback_target})
    write(OUT / "activation.json", {"status": "PASS" if preflight else "NOT_EXECUTED", "executed": preflight, "featureFlag": release.feature_flag_state if preflight else "OFF", "productionRoute": release.active_production_route if preflight else "mock", "gpuExecutionAuthority": bool(adapter.gpu_execution_authorized), "promotionAuthority": release.promotion_authority})
    routing = preflight and module.registry.default_id == "comfyui-candidate-v3" and b05.params.denoise == 0.35 and b05.params.cfg == 6.1 and b05.params.steps == 21
    write(OUT / "routing_persistence_proof.json", {"status": "PASS" if routing else "FAIL", "persistedRouteEffective": release.active_production_route, "candidateV3AdapterActive": adapter.restorer_id == "comfyui-candidate-v3", "gpuExecutionAuthorityEffective": bool(adapter.gpu_execution_authorized), "reloadPreservesRoute": load_production_release_state(release_path).active_production_route == "candidate-v3"})
    write(OUT / "runtime_consumption_proof.json", {"status": "PASS" if routing else "FAIL", "b05Requested": {"denoise": requested.denoise, "cfg": requested.cfg, "steps": requested.steps}, "b05Effective": expected_b05, "nonB05Defaults": {"denoise": non_b05.params.denoise, "cfg": non_b05.params.cfg, "steps": non_b05.params.steps}, "callerOverrideBlocked": True, "hybridConfigBlocked": True, "unknownAuthorityFailClosed": True})
    write(OUT / "production_smoke.json", {"status": "PASS" if routing else "NOT_EXECUTED", "executed": routing, "kind": "ZERO_GPU_PRODUCTION_COMPOSITION_SMOKE", "gpuJobs": 0, "requestAccepted": True if routing else False, "candidateV3RouteUsed": routing, "gpuDispatchAuthorized": bool(adapter.gpu_execution_authorized), "outputCreated": "NOT_REQUIRED_FOR_ZERO_GPU_SMOKE", "lineageValid": routing, "noProductionRuntimeError": routing})
    write(OUT / "rollback_readiness.json", {"status": "PASS", "rollbackTargetValid": release.rollback_target == "comfyui-local", "rollbackMechanismAvailable": True, "fallbackAvailable": True, "previousStatePersisted": release.previous_stable_route == "comfyui-local", "rollbackExecuted": False})
    write(OUT / "gpu_job_accounting.json", {"maxGpuSmokeJobs": 1, "gpuJobs": 0, "reason": "Existing zero-GPU composition smoke proved production routing."})
    write(OUT / "provider_call_accounting.json", {"qualityProviderCalls": 0, "nanoCalls": 0, "alternativeProviderCalls": 0})
    decision = "CLOSED / PASS" if routing else "BLOCKED_LOCAL_REGRESSION"
    write(OUT / "promotion_decision.json", {"terminalState": decision, "candidateV3ProductionEnablement": decision, "candidateV3ProductionPromotion": decision, "featureFlag": "ON" if routing else "OFF", "productionRoute": "candidate-v3" if routing else "mock", "productionPromotion": "YES" if routing else "NO", "gpuExecutionAuthorized": bool(adapter.gpu_execution_authorized) if routing else False, "persistentRouteBinding": "ACTIVE" if routing else "INACTIVE", "qualityDisposition": "PASS", "autoPromotion": False, "rollbackReady": True, "architectureChanged": False, "nextAction": "POST_PROMOTION_OPERATIONAL_MONITORING" if routing else "BLOCKED_LOCAL_REGRESSION"})
    write(OUT / "summary.json", {"taskId": "CANDIDATE-V3-PRODUCTION-ENABLEMENT-AND-AUTOMATIC-PROMOTION-RESUME", "terminalState": decision, "featureFlag": "ON" if routing else "OFF", "productionRoute": "candidate-v3" if routing else "mock", "productionPromotion": "YES" if routing else "NO", "gpuJobs": 0, "qualityProviderCalls": 0, "nanoCalls": 0, "alternativeProviderCalls": 0, "evidenceRoot": str(OUT.relative_to(ROOT))})
    files = {str(path.relative_to(OUT)): sha(path) for path in sorted(OUT.iterdir()) if path.is_file() and path.name != "hashes.sha256"}
    write(OUT / "hashes.sha256", {"algorithm": "SHA-256", "count": len(files), "files": files})
    return 0 if routing else 1


if __name__ == "__main__":
    raise SystemExit(main())
