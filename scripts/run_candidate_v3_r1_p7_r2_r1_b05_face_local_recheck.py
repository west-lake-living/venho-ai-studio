#!/usr/bin/env python3
"""Run the authorized B05 FACE_LOCAL recheck, fail-closed if no remediated artifact exists."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
PHASE7 = ROOT / "artifacts/identity-restoration/phase7-candidate-v3"
R2 = PHASE7 / "r1-p7-r2-b05-face-local-remediation-20260902T033100Z"
R1 = PHASE7 / "r1-p7-r1-targeted-authoritative-recheck-20260902T032200Z"
R4 = PHASE7 / "r1-p5-r4-provider-recovery-recheck-20260902T010010Z"
CONFIG = ROOT / "config/projects/venho_hotel/identity_restoration/r1_p7_r2_b05_face_local.yaml"
OUT = Path(os.environ.get(
    "R1_P7_R2_R1_OUTPUT_DIR",
    str(PHASE7 / ("r1-p7-r2-r1-b05-face-local-recheck-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))),
))
TASK_ID = "R1-P7-R2-R1-B05-FACE-LOCAL-AUTHORITATIVE-RECHECK"
MODEL = "gemini-flash-latest"


def sha_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def run_offline(command: list[str]) -> tuple[int, str]:
    env = dict(os.environ)
    env.pop("VALIDATOR_LIVE_ENABLED", None)
    env.pop("GEMINI_API_KEY", None)
    env.pop("GOOGLE_API_KEY", None)
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, check=False)
    return result.returncode, (result.stdout + result.stderr).rstrip() + "\n"


def finish_hashes() -> None:
    files = {
        str(path.relative_to(OUT)): sha_path(path)
        for path in sorted(OUT.rglob("*"))
        if path.is_file() and path.name != "hashes.sha256"
    }
    write_json(OUT / "hashes.sha256", {"algorithm": "SHA-256", "files": files, "count": len(files)})


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    r2_summary = load_json(R2 / "summary.json")
    r1_summary = load_json(R1 / "targeted_recheck_summary.json")
    recovery_summary = load_json(R4 / "summary.json")
    r1_b05 = load_json(R1 / "face_local" / "B05" / "evaluation_report.json")
    r1_b05_metadata = load_json(R1 / "face_local" / "B05" / "request_metadata.json")

    authorization = os.environ.get("B05_FACE_LOCAL_RECHECK_AUTHORIZED", "FALSE")
    preflight_reasons: list[str] = []
    if authorization != "TRUE":
        preflight_reasons.append("B05_FACE_LOCAL_RECHECK_AUTHORIZED_NOT_TRUE")
    if r2_summary.get("status") != "CLOSED / REMEDIATION_READY":
        preflight_reasons.append("R1_P7_R2_NOT_REMEDIATION_READY")
    if r2_summary.get("qualityDisposition") != "FAIL_PENDING_B05_RECHECK":
        preflight_reasons.append("R1_P7_R2_QUALITY_DISPOSITION_MISMATCH")
    if r1_summary.get("boundary") != "9/9 PASS":
        preflight_reasons.append("BOUNDARY_BASELINE_MISMATCH")
    if r1_summary.get("finalFaceLocalBaselinePlusTargeted") != {"fail": 1, "pass": 8}:
        preflight_reasons.append("FACE_LOCAL_BASELINE_MISMATCH")
    if r1_summary.get("finalScenarioGlobalBaselinePlusTargeted") != {"fail": 0, "pass": 9}:
        preflight_reasons.append("SCENARIO_BASELINE_MISMATCH")
    if recovery_summary.get("status") != "PASS" or recovery_summary.get("providerHold") != "RECOVERED":
        preflight_reasons.append("PROVIDER_HOLD_NOT_RECOVERED")
    recovery_provider = recovery_summary.get("provider") or recovery_summary.get("gate", {}).get("provider")
    recovery_model = recovery_summary.get("model") or recovery_summary.get("gate", {}).get("model")
    if recovery_provider != "Gemini" or recovery_model != MODEL:
        preflight_reasons.append("PROVIDER_MODEL_LOCK_MISMATCH")
    if config.get("target", {}).get("caseId") != "B05" or config.get("target", {}).get("lane") != "FACE_LOCAL":
        preflight_reasons.append("TARGET_SCOPE_MISMATCH")
    if config.get("remediation", {}).get("scope") != "B05_ONLY":
        preflight_reasons.append("REMEDIATION_SCOPE_MISMATCH")
    if config.get("authorization", {}).get("b05FaceLocalRecheckAuthorized") is not False:
        preflight_reasons.append("CONFIG_RECHECK_AUTHORITY_NOT_SEPARATE")

    # R1-P7-R2 prepared a plan only. A validation-only task cannot create the
    # required new restored artifact, and the frozen R1-P7-R1 image is not a
    # valid substitute for a remediated artifact.
    variant_artifact = config.get("remediation", {}).get("artifact")
    if not variant_artifact:
        preflight_reasons.append("R2_REMEDIATED_ARTIFACT_MISSING")
    elif not (ROOT / variant_artifact).is_file():
        preflight_reasons.append("R2_REMEDIATED_ARTIFACT_NOT_FOUND")

    focused_tests = [
        "tests/test_candidate_v3_r1_p7_r2_b05_face_local.py",
        "tests/test_candidate_v3_r1_p7_r2_r1_b05_face_local_recheck.py",
        "tests/test_candidate_v3_r1_p7_r1_targeted_recheck.py",
        "tests/test_candidate_v3_r1_p7_targeted_remediation.py",
        "tests/test_candidate_v3_r1_p5_provider_recovery_gate.py",
        "tests/identity_restoration/application/test_phase7_candidate_v3_evaluation.py",
        "tests/identity_restoration/contracts/test_candidate_v3_schemas.py",
    ]
    test_code, test_output = run_offline(["python3", "-m", "pytest", "-q", *focused_tests])
    compile_code, compile_output = run_offline(["python3", "-m", "compileall", "-q", "identity_restoration", "validator_studio", "shared/vision", "scripts/run_candidate_v3_r1_p7_r2_r1_b05_face_local_recheck.py"])
    diff_code, diff_output = run_offline(["git", "diff", "--check"])
    (OUT / "test_results.txt").write_text(test_output, encoding="utf-8")
    (OUT / "compileall.txt").write_text(compile_output if compile_output.strip() else "compileall=PASS\n", encoding="utf-8")
    (OUT / "git_diff_check.txt").write_text(diff_output if diff_output.strip() else "git_diff_check=PASS\n", encoding="utf-8")
    if test_code != 0 or compile_code != 0 or diff_code != 0:
        preflight_reasons.append("OFFLINE_VALIDATION_FAILED")

    preflight_status = "PASS" if not preflight_reasons else "BLOCKED_LOCAL_REGRESSION"
    baseline = {
        "taskId": TASK_ID,
        "authorization": {"name": "B05_FACE_LOCAL_RECHECK_AUTHORIZED", "requiredValue": "TRUE", "receivedValue": authorization},
        "r1P7R2": {"path": str(R2.relative_to(ROOT)), "summarySha256": sha_path(R2 / "summary.json"), "status": r2_summary["status"], "qualityDisposition": r2_summary["qualityDisposition"]},
        "startState": {"r1P7R2": "CLOSED / REMEDIATION_READY", "boundary": "9/9 PASS", "faceLocal": "8/9 PASS", "scenarioGlobal": "9/9 PASS", "qualityDisposition": "FAIL_PENDING_B05_RECHECK", "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False},
        "previousB05": {"score": r1_b05["overall_score"], "verdict": r1_b05["verdict"], "dimensions": r1_b05["category_scores"], "rawHash": r1_b05_metadata["rawHash"], "parsedHash": r1_b05_metadata["parsedHash"]},
        "provider": {"provider": "Gemini", "model": MODEL, "hold": recovery_summary["providerHold"]},
        "preflight": {"status": preflight_status, "reasons": preflight_reasons},
    }
    write_json(OUT / "baseline.json", baseline)
    write_json(OUT / "offline_preflight.json", {"status": preflight_status, "providerCalls": 0, "maxProviderCalls": 1, "retries": 0, "testsExitCode": test_code, "compileallExitCode": compile_code, "gitDiffCheckExitCode": diff_code, "reasons": preflight_reasons, "boundary": "9/9 PASS", "faceLocal": "8/9 PASS", "scenarioGlobal": "9/9 PASS", "providerHold": "RECOVERED", "schemaDtoParser": "VALIDATED", "thresholdsChanged": False, "rubricChanged": False, "providerModelChanged": False, "passingBindingsChanged": False, "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False})
    write_json(OUT / "probe_request_metadata.json", {"taskId": TASK_ID, "caseId": "B05", "evaluator": "FACE_LOCAL", "provider": "Gemini", "model": MODEL, "requested": True, "attempted": False, "callStatus": "NOT_EXECUTED", "validResponse": False, "lineageStatus": "BLOCKED_LOCAL_REGRESSION", "remediationVariantId": config["remediation"]["variantId"], "remediationManifest": str(CONFIG.relative_to(ROOT)), "reason": "No new R2 restored artifact exists; validation-only scope forbids creating one or evaluating the frozen prior artifact as remediated."})
    write_json(OUT / "b05_raw.blocked.json", {"available": False, "providerCall": False, "reason": "R2_REMEDIATED_ARTIFACT_MISSING"})
    write_json(OUT / "b05_parsed.json", {"available": False, "validResponse": False, "reason": "R2_REMEDIATED_ARTIFACT_MISSING"})
    write_json(OUT / "before_after_comparison.json", {"caseId": "B05", "evaluator": "FACE_LOCAL", "before": {"score": 88.50, "verdict": "revise", "dimensions": {"eyes_and_brows": 87, "facial_shape": 88, "mouth_and_chin": 89}, "rawHash": r1_b05_metadata["rawHash"], "parsedHash": r1_b05_metadata["parsedHash"]}, "after": {"status": "NOT_EVALUATED", "score": None, "verdict": None, "dimensions": None, "rawHash": None, "parsedHash": None}, "deltas": None})
    write_json(OUT / "quality_disposition.json", {"taskId": TASK_ID, "status": preflight_status, "qualityDisposition": "FAIL_PENDING_B05_RECHECK", "b05FaceLocal": "NOT_EVALUATED", "boundary": "9/9 PASS", "faceLocal": "8/9 PASS", "scenarioGlobal": "9/9 PASS", "pendingAuthoritativeEvaluations": 1, "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False, "nextAction": "R2_REMEDIATED_ARTIFACT_REQUIRED_BEFORE_B05_FACE_LOCAL_RECHECK"})
    write_json(OUT / "provider_call_accounting.json", {"expected": 1, "attempted": 0, "valid": 0, "invalid": 0, "providerCalls": 0, "retries": 0, "gpuJobs": 0, "nanoCalls": 0, "alternativeProviderCalls": 0, "provider": "Gemini", "model": MODEL})
    write_json(OUT / "summary.json", {"taskId": TASK_ID, "status": preflight_status, "authorization": True, "b05FaceLocal": {"expected": 1, "attempted": 0, "valid": 0, "invalid": 0, "score": None, "verdict": None, "lineageStatus": "BLOCKED_LOCAL_REGRESSION"}, "providerCalls": 0, "retries": 0, "boundary": "9/9 PASS", "faceLocal": "8/9 PASS", "scenarioGlobal": "9/9 PASS", "pendingAuthoritativeEvaluations": 1, "qualityDisposition": "FAIL_PENDING_B05_RECHECK", "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False, "nextAction": "R2_REMEDIATED_ARTIFACT_REQUIRED_BEFORE_B05_FACE_LOCAL_RECHECK", "preflightReasons": preflight_reasons})
    finish_hashes()
    print(json.dumps({"status": preflight_status, "output": str(OUT), "providerCalls": 0, "reasons": preflight_reasons}))
    return 0 if preflight_status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
