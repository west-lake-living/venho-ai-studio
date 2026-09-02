#!/usr/bin/env python3
"""Resolve B05 parameter authority and fail closed when no delta is proven."""

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
P9 = PHASE7 / "r1-p9-b05-artifact-contract-final-closure-20260902T034520Z"
R2 = PHASE7 / "r1-p7-r2-b05-face-local-remediation-20260902T033100Z"
JOB = PHASE7 / "jobs/phase7-diagnostic-20260828-B05.json"
WORKFLOW = ROOT / "identity_restoration/workflows/face_restore_win_sd15_ipadapter_v3.api.json"
CONFIG = ROOT / "config/projects/venho_hotel/identity_restoration/r1_p7_r2_b05_face_local.yaml"
OUT = Path(os.environ.get(
    "R1_P10_OUTPUT_DIR",
    str(PHASE7 / ("r1-p10-b05-parameter-resolution-final-closure-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))),
))
TASK_ID = "R1-P10-B05-PARAMETER-RESOLUTION-AND-FINAL-CLOSURE"


def sha_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


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


def build_parameter_matrix(job: dict[str, Any], workflow: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    bound = job["lineage"]["bridge"]["adapterEvidence"]["boundConfig"]
    workflow_sha = sha_path(WORKFLOW)
    return [
        {"parameter": "denoise", "currentValue": bound["denoise"], "allowedDomain": {"min": 0.05, "max": 0.75}, "authoritySource": ["identity_restoration/domain/value_objects.py:RestorationParams", str(WORKFLOW.relative_to(ROOT)), "B05 immutable job boundConfig"], "expectedEffect": "face restoration strength/detail versus source preservation", "b05Relevance": "HIGH", "passingCaseRisk": "UNRESOLVED", "workflowInputEvidence": workflow.get("12", {}).get("inputs", {}).get("denoise"), "workflowHash": workflow_sha},
        {"parameter": "cfg", "currentValue": bound["cfg"], "allowedDomain": {"min": 1.0, "max": 12.0}, "authoritySource": ["identity_restoration/domain/value_objects.py:RestorationParams", str(WORKFLOW.relative_to(ROOT)), "B05 immutable job boundConfig"], "expectedEffect": "conditioning adherence", "b05Relevance": "POSSIBLE", "passingCaseRisk": "UNRESOLVED", "workflowInputEvidence": workflow.get("12", {}).get("inputs", {}).get("cfg"), "workflowHash": workflow_sha},
        {"parameter": "steps", "currentValue": bound["steps"], "allowedDomain": {"min": 8, "max": 60}, "authoritySource": ["identity_restoration/domain/value_objects.py:RestorationParams", str(WORKFLOW.relative_to(ROOT)), "B05 immutable job boundConfig"], "expectedEffect": "sampling refinement", "b05Relevance": "POSSIBLE", "passingCaseRisk": "UNRESOLVED", "workflowInputEvidence": workflow.get("12", {}).get("inputs", {}).get("steps"), "workflowHash": workflow_sha},
    ]


def main() -> int:
    if OUT.exists() and any(OUT.iterdir()):
        raise SystemExit(f"refusing to overwrite evidence directory: {OUT}")
    OUT.mkdir(parents=True, exist_ok=True)
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    job = load_json(JOB)
    workflow = load_json(WORKFLOW)
    p9_summary = load_json(P9 / "summary.json")
    p9_contract = load_json(P9 / "artifact_contract.json")
    r2_summary = load_json(R2 / "summary.json")
    matrix = build_parameter_matrix(job, workflow, config)
    start_reasons: list[str] = []
    if os.environ.get("R1_P10_B05_PARAMETER_RESOLUTION_AND_CLOSURE_AUTHORIZED") != "TRUE":
        start_reasons.append("R1_P10_AUTHORIZATION_NOT_TRUE")
    if p9_summary.get("status") != "BLOCKED / REMEDIATION_PARAMETER_UNRESOLVED":
        start_reasons.append("R1_P9_START_STATE_MISMATCH")
    if r2_summary.get("status") != "CLOSED / REMEDIATION_READY":
        start_reasons.append("R1_P7_R2_START_STATE_MISMATCH")

    selection_rule_found = False
    unresolved = [
        "No repository-approved B05 geometry-keyed preset exists.",
        "No deterministic extreme-yaw/small-face rule selects a new restore value.",
        "Passing peers use the same denoise=0.35/cfg=6.0/steps=20 baseline; they do not authorize a delta.",
        "R1-P7-R2 proves face-detail intent but no concrete restore delta.",
    ]
    write_json(OUT / "baseline.json", {"taskId": TASK_ID, "authorization": {"name": "R1_P10_B05_PARAMETER_RESOLUTION_AND_CLOSURE_AUTHORIZED", "requiredValue": "TRUE", "receivedValue": os.environ.get("R1_P10_B05_PARAMETER_RESOLUTION_AND_CLOSURE_AUTHORIZED")}, "startState": {"r1P9": p9_summary.get("status"), "blocker": "Concrete R2 restore delta is not evidence-backed", "r2": r2_summary.get("status"), "boundary": "9/9 PASS", "faceLocal": "8/9 PASS", "scenarioGlobal": "9/9 PASS", "pending": 1, "qualityDisposition": "FAIL_PENDING_B05_RECHECK", "provider": "Gemini", "model": "gemini-flash-latest", "providerHold": "RECOVERED", "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False}, "startReasons": start_reasons, "sourceEvidence": {"p9": str(P9.relative_to(ROOT)), "r2": str(R2.relative_to(ROOT))}})
    write_json(OUT / "parameter_authority_matrix.json", {"caseId": "B05", "geometry": {"faceScale": 0.072265625, "yaw": -49.07742057379534}, "matrix": matrix, "authoritativeSelectionRuleFound": selection_rule_found, "unresolved": unresolved})
    write_json(OUT / "selected_remediation_delta.json", {"status": "BLOCKED / HUMAN_PARAMETER_DECISION_REQUIRED", "parameter": None, "before": None, "after": None, "delta": None, "selectionRule": None, "authoritySource": None, "whyThisIsNotTuning": "No evidence-backed rule selects one concrete B05 value; selecting one would be exploratory tuning."})
    write_json(OUT / "artifact_contract.json", {"status": "NOT_COMPLETABLE", "contractComplete": False, "caseId": "B05", "restoreVariantId": config["remediation"]["variantId"], "workflowId": config["remediation"]["workflow"], "currentParameters": {"denoise": 0.35, "steps": 20, "cfg": 6.0, "sampler": "euler", "scheduler": "normal", "seed": 42}, "selectedRemediationDelta": None, "outputArtifactId": None, "outputPath": None, "unresolvedParameters": unresolved})
    write_json(OUT / "artifact_contract_authority.json", {"p9ContractSha256": sha_path(P9 / "artifact_contract.json"), "workflowSha256": sha_path(WORKFLOW), "knownBaseline": p9_contract["restoreParameters"]["baseline"], "selectionRuleFound": False, "unresolved": unresolved})

    focused_tests = [
        "tests/test_candidate_v3_r1_p10_b05_parameter_resolution_final_closure.py",
        "tests/test_candidate_v3_r1_p9_b05_artifact_contract_final_closure.py",
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
    compile_code, compile_output = run_offline(["python3", "-m", "compileall", "-q", "identity_restoration", "validator_studio", "shared/vision", "scripts/run_candidate_v3_r1_p10_b05_parameter_resolution_final_closure.py"])
    diff_code, diff_output = run_offline(["git", "diff", "--check"])
    (OUT / "test_results.txt").write_text(test_output, encoding="utf-8")
    (OUT / "compileall.txt").write_text(compile_output if compile_output.strip() else "compileall=PASS\n", encoding="utf-8")
    (OUT / "git_diff_check.txt").write_text(diff_output if diff_output.strip() else "git_diff_check=PASS\n", encoding="utf-8")

    final_status = "BLOCKED / HUMAN_PARAMETER_DECISION_REQUIRED" if test_code == compile_code == diff_code == 0 and not start_reasons else "BLOCKED / LOCAL_REGRESSION"
    write_json(OUT / "artifact_materialization.json", {"status": "NOT_EXECUTED", "gpuJobs": 0, "artifactCount": 0, "reason": final_status})
    write_json(OUT / "lineage_validation.json", {"status": "NOT_EXECUTED", "artifactExists": False, "contractMatch": False, "caseScope": "B05_ONLY", "passingCasesProtected": True})
    write_json(OUT / "before_after_comparison.json", {"caseId": "B05", "before": {"score": 88.50, "verdict": "revise", "eyesBrows": 87, "facialShape": 88, "mouthChin": 89}, "after": {"status": "NOT_EVALUATED", "score": None}, "deltas": None})
    write_json(OUT / "quality_disposition.json", {"taskId": TASK_ID, "status": final_status, "boundary": "9/9 PASS", "faceLocal": "8/9 PASS", "scenarioGlobal": "9/9 PASS", "pendingAuthoritativeEvaluations": 1, "qualityDisposition": "FAIL_PENDING_B05_RECHECK", "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False, "nextAction": "HUMAN_PARAMETER_DECISION_REQUIRED"})
    write_json(OUT / "provider_call_accounting.json", {"maxProviderCalls": 1, "providerCalls": 0, "retries": 0, "nanoCalls": 0, "alternativeProviderCalls": 0})
    write_json(OUT / "gpu_job_accounting.json", {"maxGpuJobs": 1, "gpuJobs": 0, "maxArtifacts": 1, "artifactsCreated": 0})
    write_json(OUT / "summary.json", {"taskId": TASK_ID, "status": final_status, "parameterAuthority": "UNRESOLVED", "selectedDelta": None, "t0": "PASS", "t1": final_status, "t2": "NOT_EXECUTED", "t3": "NOT_EXECUTED", "t4": "NOT_EXECUTED", "t5": "NOT_EXECUTED", "t6": "NOT_EXECUTED", "providerCalls": 0, "retries": 0, "gpuJobs": 0, "nanoCalls": 0, "alternativeProviderCalls": 0, "boundary": "9/9 PASS", "faceLocal": "8/9 PASS", "scenarioGlobal": "9/9 PASS", "pendingAuthoritativeEvaluations": 1, "qualityDisposition": "FAIL_PENDING_B05_RECHECK", "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False, "nextAction": "HUMAN_PARAMETER_DECISION_REQUIRED", "unresolved": unresolved + start_reasons})
    finish_hashes()
    print(json.dumps({"status": final_status, "output": str(OUT), "providerCalls": 0, "selectionRuleFound": False, "unresolved": unresolved}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
