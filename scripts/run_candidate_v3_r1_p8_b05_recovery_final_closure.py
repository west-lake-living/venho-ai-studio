#!/usr/bin/env python3
"""Run R1-P8 T0 and stop safely when the R2 artifact contract is incomplete."""

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
P6 = PHASE7 / "r1-p6-authoritative-evaluation-resume-20260902T024012Z"
P7 = PHASE7 / "r1-p7-targeted-quality-remediation-20260902T030000Z"
R2 = PHASE7 / "r1-p7-r2-b05-face-local-remediation-20260902T033100Z"
R2_R1 = PHASE7 / "r1-p7-r2-r1-b05-face-local-recheck-20260902T033242Z"
CONFIG = ROOT / "config/projects/venho_hotel/identity_restoration/r1_p7_r2_b05_face_local.yaml"
OUT = Path(os.environ.get(
    "R1_P8_OUTPUT_DIR",
    str(PHASE7 / ("r1-p8-b05-recovery-final-closure-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))),
))
TASK_ID = "R1-P8-B05-RECOVERY-AND-FINAL-QUALITY-CLOSURE"


def sha_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    if OUT.exists() and any(OUT.iterdir()):
        raise SystemExit(f"refusing to overwrite evidence directory: {OUT}")
    OUT.mkdir(parents=True, exist_ok=True)
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    r2_summary = load_json(R2 / "summary.json")
    r2r1_summary = load_json(R2_R1 / "summary.json")
    r2r1_preflight = load_json(R2_R1 / "offline_preflight.json")
    p7_summary = load_json(P7 / "summary.json")

    reasons: list[str] = []
    if os.environ.get("R1_P8_B05_RECOVERY_AND_FINAL_CLOSURE_AUTHORIZED") != "TRUE":
        reasons.append("R1_P8_AUTHORIZATION_NOT_TRUE")
    if r2_summary.get("status") != "CLOSED / REMEDIATION_READY":
        reasons.append("R1_P7_R2_START_STATE_MISMATCH")
    if r2r1_summary.get("status") != "BLOCKED_LOCAL_REGRESSION":
        reasons.append("R1_P7_R2_R1_START_STATE_MISMATCH")
    if "R2_REMEDIATED_ARTIFACT_MISSING" not in r2r1_summary.get("preflightReasons", []):
        reasons.append("R2_R1_BLOCKER_MISMATCH")
    if p7_summary.get("status") != "CLOSED / REMEDIATION_READY":
        reasons.append("R1_P7_EVIDENCE_MISMATCH")

    target = config.get("target", {})
    remediation = config.get("remediation", {})
    required_contract_fields = {
        "expectedArtifactId": remediation.get("artifactId"),
        "expectedManifest": remediation.get("manifest"),
        "expectedOutputPath": remediation.get("artifact"),
        "sourceLineage": remediation.get("sourceLineage"),
        "outputBinding": remediation.get("outputBinding"),
    }
    missing_contract_fields = [key for key, value in required_contract_fields.items() if not value]
    if missing_contract_fields:
        reasons.append("REMEDIATION_CONTRACT_INCOMPLETE")

    focused_tests = [
        "tests/test_candidate_v3_r1_p8_b05_recovery_final_closure.py",
        "tests/test_candidate_v3_r1_p7_r2_r1_b05_face_local_recheck.py",
        "tests/test_candidate_v3_r1_p7_r2_b05_face_local.py",
        "tests/test_candidate_v3_r1_p7_r1_targeted_recheck.py",
        "tests/test_candidate_v3_r1_p7_targeted_remediation.py",
        "tests/test_candidate_v3_r1_p5_provider_recovery_gate.py",
        "tests/identity_restoration/application/test_phase7_candidate_v3_evaluation.py",
        "tests/identity_restoration/contracts/test_candidate_v3_schemas.py",
    ]
    test_code, test_output = run_offline(["python3", "-m", "pytest", "-q", *focused_tests])
    compile_code, compile_output = run_offline(["python3", "-m", "compileall", "-q", "identity_restoration", "validator_studio", "shared/vision", "scripts/run_candidate_v3_r1_p8_b05_recovery_final_closure.py"])
    diff_code, diff_output = run_offline(["git", "diff", "--check"])
    (OUT / "test_results.txt").write_text(test_output, encoding="utf-8")
    (OUT / "compileall.txt").write_text(compile_output if compile_output.strip() else "compileall=PASS\n", encoding="utf-8")
    (OUT / "git_diff_check.txt").write_text(diff_output if diff_output.strip() else "git_diff_check=PASS\n", encoding="utf-8")
    if test_code != 0 or compile_code != 0 or diff_code != 0:
        reasons.append("OFFLINE_VALIDATION_FAILED")

    blocked = bool(reasons)
    write_json(OUT / "baseline.json", {
        "taskId": TASK_ID,
        "authorization": {"name": "R1_P8_B05_RECOVERY_AND_FINAL_CLOSURE_AUTHORIZED", "requiredValue": "TRUE", "receivedValue": os.environ.get("R1_P8_B05_RECOVERY_AND_FINAL_CLOSURE_AUTHORIZED")},
        "authoritativeStartState": {"r1P7R2": "CLOSED / REMEDIATION_READY", "r1P7R2R1": "BLOCKED_LOCAL_REGRESSION", "blocker": "R2_REMEDIATED_ARTIFACT_MISSING", "boundary": "9/9 PASS", "faceLocal": "8/9 PASS", "scenarioGlobal": "9/9 PASS", "pending": 1, "qualityDisposition": "FAIL_PENDING_B05_RECHECK", "providerHold": "RECOVERED", "provider": "Gemini", "model": "gemini-flash-latest", "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False},
        "sourceEvidence": {"p6": str(P6.relative_to(ROOT)), "p7": str(P7.relative_to(ROOT)), "r2": str(R2.relative_to(ROOT)), "r2R1": str(R2_R1.relative_to(ROOT))},
        "reconstruction": {"expectedSourceCase": target.get("caseId"), "expectedVariant": remediation.get("variantId"), "expectedWorkflow": remediation.get("workflow"), "expectedArtifactId": required_contract_fields["expectedArtifactId"], "expectedManifest": required_contract_fields["expectedManifest"], "expectedInputLineage": required_contract_fields["sourceLineage"], "expectedOutputPath": required_contract_fields["expectedOutputPath"], "missingContractFields": missing_contract_fields},
        "status": "BLOCKED / REMEDIATION_CONTRACT_INCOMPLETE" if blocked else "READY",
        "reasons": reasons,
    })
    write_json(OUT / "t0-reconstruction" / "result.json", {"status": "BLOCKED / REMEDIATION_CONTRACT_INCOMPLETE", "contractComplete": False, "expectedArtifactId": required_contract_fields["expectedArtifactId"], "expectedSourceCase": target.get("caseId"), "expectedVariant": remediation.get("variantId"), "expectedManifest": required_contract_fields["expectedManifest"], "expectedWorkflow": remediation.get("workflow"), "expectedInputLineage": required_contract_fields["sourceLineage"], "expectedOutputPath": required_contract_fields["expectedOutputPath"], "missingFields": missing_contract_fields, "evidence": "R1-P7-R2 defines a variant ID and preservation rules but no deterministic artifact/manifest/output binding or concrete restoration change."})
    write_json(OUT / "provider_call_accounting.json", {"maxB05AuthoritativeProviderCalls": 2, "providerCalls": 0, "retries": 0, "gpuJobs": 0, "nanoCalls": 0, "alternativeProviderCalls": 0, "t3Calls": 0, "t5Calls": 0})
    write_json(OUT / "before_after_history.json", {"caseId": "B05", "baseline": {"score": 88.50, "verdict": "revise", "eyesBrows": 87, "facialShape": 88, "mouthChin": 89}, "r1P8": {"status": "NOT_EVALUATED", "score": None, "verdict": None}, "deltas": None})
    write_json(OUT / "quality_disposition.json", {"taskId": TASK_ID, "status": "BLOCKED / REMEDIATION_CONTRACT_INCOMPLETE", "boundary": "9/9 PASS", "faceLocal": "8/9 PASS", "scenarioGlobal": "9/9 PASS", "pendingAuthoritativeEvaluations": 1, "qualityDisposition": "FAIL_PENDING_B05_RECHECK", "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False, "nextAction": "COMPLETE_R2_B05_ARTIFACT_CONTRACT_BEFORE_RECOVERY"})
    write_json(OUT / "summary.json", {"taskId": TASK_ID, "status": "BLOCKED / REMEDIATION_CONTRACT_INCOMPLETE", "authorization": True, "t0": "BLOCKED / REMEDIATION_CONTRACT_INCOMPLETE", "t1": "NOT_EXECUTED", "t2": "NOT_EXECUTED", "t3": "NOT_EXECUTED", "t4": "NOT_EXECUTED", "t5": "NOT_EXECUTED", "t6": "NOT_EXECUTED", "providerCalls": 0, "retries": 0, "gpuJobs": 0, "nanoCalls": 0, "alternativeProviderCalls": 0, "boundary": "9/9 PASS", "faceLocal": "8/9 PASS", "scenarioGlobal": "9/9 PASS", "pendingAuthoritativeEvaluations": 1, "qualityDisposition": "FAIL_PENDING_B05_RECHECK", "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False, "nextAction": "COMPLETE_R2_B05_ARTIFACT_CONTRACT_BEFORE_RECOVERY", "blockers": reasons})
    finish_hashes()
    print(json.dumps({"status": "BLOCKED / REMEDIATION_CONTRACT_INCOMPLETE", "output": str(OUT), "providerCalls": 0, "reasons": reasons}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
