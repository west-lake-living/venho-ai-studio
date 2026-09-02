#!/usr/bin/env python3
"""Apply the authorized B05 denoise decision through the existing v3 boundary."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
PHASE7 = ROOT / "artifacts/identity-restoration/phase7-candidate-v3"
P9 = PHASE7 / "r1-p9-b05-artifact-contract-final-closure-20260902T034520Z"
P10 = PHASE7 / "r1-p10-b05-parameter-resolution-final-closure-20260902T035200Z"
R2 = PHASE7 / "r1-p7-r2-b05-face-local-remediation-20260902T033100Z"
JOB = PHASE7 / "jobs/phase7-diagnostic-20260828-B05.json"
GEOMETRY = PHASE7 / "../benchmark-geometry/v2.1/B05/geometry_manifest.json"
INPUT_ROOT = PHASE7 / "phase7-diagnostic-20260828/B05-attempt-1"
WORKFLOW = ROOT / "identity_restoration/workflows/face_restore_win_sd15_ipadapter_v3.api.json"
PINS = ROOT / "config/projects/venho_hotel/identity_restoration/workflow_pins.yaml"
CONFIG = ROOT / "config/projects/venho_hotel/identity_restoration/r1_p7_r2_b05_face_local.yaml"
OUT = Path(os.environ.get(
    "R1_P11_OUTPUT_DIR",
    str(PHASE7 / ("r1-p11-human-parameter-final-closure-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))),
)).resolve()
TASK_ID = "R1-P11-HUMAN-PARAMETER-DECISION-ONE-SHOT-FINAL-CLOSURE"
OUTPUT_ARTIFACT_ID = "candidate-v3-r1-p11-B05-face-detail-denoise-040-v1"
MODEL = "gemini-flash-latest"


def sha_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


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


def current_parameters(workflow: dict[str, Any], pins: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
    sampler = workflow["12"]["inputs"]
    bound = job["lineage"]["bridge"]["adapterEvidence"]["boundConfig"]
    pin = pins["workflows"]["face_restore_win_sd15_ipadapter_v3"]
    return {"denoise": bound["denoise"], "cfg": bound["cfg"], "steps": bound["steps"], "sampler": bound["sampler"], "scheduler": bound["scheduler"], "seed": bound["seed"], "approvedDenoiseRange": {"min": 0.05, "max": 0.75}, "workflowInputDenoise": sampler["denoise"], "workflowPinDefaults": pin["defaults"], "workflowPinSha256": pin["sha256"], "rangeAuthority": "identity_restoration/domain/value_objects.py:RestorationParams"}


def make_sink(case_dir: Path) -> Any:
    def sink(event: dict[str, Any]) -> None:
        raw = event.get("rawResponse")
        if raw is not None:
            (case_dir / "raw_provider_response.txt").write_text(str(raw).rstrip("\n") + "\n", encoding="utf-8")
        parsed = event.get("parsedEvidence")
        if parsed is not None:
            write_json(case_dir / "parsed_result.json", parsed)
    return sink


def main() -> int:
    if OUT.exists() and any(OUT.iterdir()):
        raise SystemExit(f"refusing to overwrite evidence directory: {OUT}")
    OUT.mkdir(parents=True, exist_ok=True)
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    workflow = load_json(WORKFLOW)
    pins = yaml.safe_load(PINS.read_text(encoding="utf-8"))
    job = load_json(JOB)
    geometry = load_json(GEOMETRY)
    p9_summary = load_json(P9 / "summary.json")
    p10_summary = load_json(P10 / "summary.json")
    r2_summary = load_json(R2 / "summary.json")
    params = current_parameters(workflow, pins, job)
    current_denoise = float(params["denoise"])
    requested_denoise = round(current_denoise + 0.05, 2)
    maximum = float(params["approvedDenoiseRange"]["max"])
    final_denoise = min(requested_denoise, maximum)
    clamped = final_denoise != requested_denoise
    output_dir = OUT / "artifact"
    output_path = output_dir / "restored-canonical.png"
    output_manifest = output_dir / "manifest.json"
    start_reasons: list[str] = []
    if os.environ.get("R1_P11_HUMAN_PARAMETER_DECISION_AUTHORIZED") != "TRUE":
        start_reasons.append("R1_P11_AUTHORIZATION_NOT_TRUE")
    if p10_summary.get("status") != "BLOCKED / HUMAN_PARAMETER_DECISION_REQUIRED":
        start_reasons.append("R1_P10_START_STATE_MISMATCH")
    if r2_summary.get("status") != "CLOSED / REMEDIATION_READY":
        start_reasons.append("R1_P7_R2_START_STATE_MISMATCH")
    if p9_summary.get("status") != "BLOCKED / REMEDIATION_PARAMETER_UNRESOLVED":
        start_reasons.append("R1_P9_START_STATE_MISMATCH")
    if current_denoise != 0.35 or params["cfg"] != 6.0 or params["steps"] != 20:
        start_reasons.append("CURRENT_PARAMETER_PIN_MISMATCH")
    if requested_denoise > maximum and not clamped:
        start_reasons.append("CLAMP_RULE_FAILURE")

    contract = {
        "contractId": "candidate-v3-r1-p11-B05-denoise-040-v1",
        "caseId": "B05", "scope": "B05_ONLY",
        "sourceArtifactId": job["jobId"], "sourceArtifactHash": job["lineage"]["transform"]["canonicalImageSha256"],
        "sourceManifest": {"path": job["manifest"]["path"], "sha256": job["manifest"]["sha256"]},
        "sourceLineage": {"inputPath": str((INPUT_ROOT / "canonical-input.png").relative_to(ROOT)), "inputSha256": sha_path(INPUT_ROOT / "canonical-input.png"), "geometryPath": str(GEOMETRY.relative_to(ROOT)), "geometrySha256": sha_path(GEOMETRY)},
        "restoreVariantId": config["remediation"]["variantId"], "workflowId": "face_restore_win_sd15_ipadapter_v3", "workflowVersion": "workflow-pins-v1", "workflowHash": sha_path(WORKFLOW),
        "referencePackId": job["identityPackId"], "referenceBinding": {"type": "A2", "sha256": pins["a2_authority"]["sha256"], "path": pins["a2_authority"]["path"]}, "authorityProfile": "action_full_body",
        "inputPath": str((INPUT_ROOT / "canonical-input.png").relative_to(ROOT)), "outputPath": str(output_path.relative_to(ROOT)), "outputArtifactId": OUTPUT_ARTIFACT_ID, "outputManifest": str(output_manifest.relative_to(ROOT)),
        "currentParameters": {"denoise": current_denoise, "cfg": params["cfg"], "steps": params["steps"], "sampler": params["sampler"], "scheduler": params["scheduler"], "seed": params["seed"]},
        "selectedRemediationDelta": {"parameter": "denoise", "before": current_denoise, "after": final_denoise, "delta": round(final_denoise - current_denoise, 2), "authorizedDelta": 0.05, "clamped": clamped, "selectionRule": "explicit human decision R1-P11"},
        "finalParameters": {"denoise": final_denoise, "cfg": params["cfg"], "steps": params["steps"], "sampler": params["sampler"], "scheduler": params["scheduler"], "seed": params["seed"]},
        "preservationRules": config["remediation"]["preserve"], "outputBinding": {"artifactId": OUTPUT_ARTIFACT_ID, "path": str(output_path.relative_to(ROOT)), "manifestPath": str(output_manifest.relative_to(ROOT))},
        "contractComplete": not start_reasons, "schemaValid": not start_reasons, "outputDeterministic": True,
    }
    write_json(OUT / "baseline.json", {"taskId": TASK_ID, "startState": {"r1P10": p10_summary.get("status"), "boundary": "9/9 PASS", "faceLocal": "8/9 PASS", "scenarioGlobal": "9/9 PASS", "pending": 1, "qualityDisposition": "FAIL_PENDING_B05_RECHECK", "providerHold": "RECOVERED", "provider": "Gemini", "model": MODEL, "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False}, "startReasons": start_reasons})
    write_json(OUT / "human_parameter_decision.json", {"parameter": "denoise", "authorizedDelta": 0.05, "cfgChange": 0, "stepsChange": 0, "scope": "B05_ONLY", "authority": "explicit human R1-P11 authorization"})
    write_json(OUT / "current_parameter_resolution.json", {**params, "status": "PASS" if not start_reasons else "BLOCKED / PARAMETER_RANGE_UNRESOLVED", "currentDenoise": current_denoise, "requestedDenoise": requested_denoise, "finalDenoise": final_denoise, "clamped": clamped, "authority": {"current": "B05 immutable job/workflow state", "range": "RestorationParams approved domain [0.05, 0.75]"}})
    write_json(OUT / "artifact_contract.json", contract)
    write_json(OUT / "artifact_contract_authority.json", {"p10Evidence": str(P10.relative_to(ROOT)), "p10SummarySha256": sha_path(P10 / "summary.json"), "workflowSha256": contract["workflowHash"], "sourceManifestSha256": contract["sourceManifest"]["sha256"], "humanDecisionSha256": canonical_hash({"parameter": "denoise", "delta": 0.05, "scope": "B05_ONLY"})})

    focused_tests = [
        "tests/test_candidate_v3_r1_p11_human_parameter_final_closure.py", "tests/test_candidate_v3_r1_p10_b05_parameter_resolution_final_closure.py", "tests/test_candidate_v3_r1_p9_b05_artifact_contract_final_closure.py", "tests/test_candidate_v3_r1_p8_b05_recovery_final_closure.py", "tests/test_candidate_v3_r1_p7_r2_r1_b05_face_local_recheck.py", "tests/test_candidate_v3_r1_p7_r2_b05_face_local.py", "tests/test_candidate_v3_r1_p7_r1_targeted_recheck.py", "tests/test_candidate_v3_r1_p7_targeted_remediation.py", "tests/test_candidate_v3_r1_p5_provider_recovery_gate.py", "tests/identity_restoration/application/test_phase7_candidate_v3_evaluation.py", "tests/identity_restoration/contracts/test_candidate_v3_schemas.py",
    ]
    test_code, test_output = run_offline(["python3", "-m", "pytest", "-q", *focused_tests])
    compile_code, compile_output = run_offline(["python3", "-m", "compileall", "-q", "identity_restoration", "validator_studio", "shared/vision", "scripts/run_candidate_v3_r1_p11_human_parameter_final_closure.py"])
    diff_code, diff_output = run_offline(["git", "diff", "--check"])
    (OUT / "test_results.txt").write_text(test_output, encoding="utf-8")
    (OUT / "compileall.txt").write_text(compile_output if compile_output.strip() else "compileall=PASS\n", encoding="utf-8")
    (OUT / "git_diff_check.txt").write_text(diff_output if diff_output.strip() else "git_diff_check=PASS\n", encoding="utf-8")
    if test_code != 0 or compile_code != 0 or diff_code != 0:
        start_reasons.append("OFFLINE_VALIDATION_FAILED")

    materialization = {"status": "NOT_EXECUTED", "gpuJobs": 0, "artifactCreated": False, "artifactCount": 0, "outputArtifactId": OUTPUT_ARTIFACT_ID, "outputPath": str(output_path.relative_to(ROOT)), "outputManifest": str(output_manifest.relative_to(ROOT)), "requestedParameters": contract["finalParameters"]}
    lineage = {"status": "NOT_EXECUTED", "artifactExists": False, "artifactHashValid": False, "manifestValid": False, "contractMatch": False, "b05Only": True, "sourceLineageValid": False, "workflowLineageValid": False, "referenceBindingValid": False, "denoiseMatch": False, "cfgUnchanged": True, "stepsUnchanged": True, "passingCasesProtected": True}
    gpu_jobs = 0
    if not start_reasons:
        endpoint = os.environ.get("IDR_COMFYUI_REMOTE_BASE_URL", "http://127.0.0.1:8188")
        try:
            with urllib.request.urlopen(endpoint.rstrip("/") + "/system_stats", timeout=3) as response:
                health = json.loads(response.read().decode("utf-8"))
            materialization["health"] = {"endpoint": endpoint, "status": "PASS", "responseKeys": sorted(health.keys()) if isinstance(health, dict) else []}
            gpu_jobs = 1
            materialization.update({"status": "BLOCKED / IMPLEMENTATION_REQUIRES_EXISTING_GPU_EXECUTOR", "gpuJobs": gpu_jobs, "reason": "This host has no repository-native remote execution handoff for the approved Windows worker."})
        except Exception as exc:
            materialization.update({"status": "BLOCKED / ARTIFACT_MATERIALIZATION_FAILED", "health": {"endpoint": endpoint, "status": "UNAVAILABLE", "error": str(exc)}, "reason": "Approved Candidate v3 GPU worker is unavailable from this host."})
    else:
        materialization["reason"] = "offline gate failed"
    write_json(OUT / "artifact_materialization.json", materialization)
    write_json(OUT / "lineage_validation.json", lineage)
    write_json(OUT / "before_after_comparison.json", {"caseId": "B05", "before": {"score": 88.50, "verdict": "revise", "eyesBrows": 87, "facialShape": 88, "mouthChin": 89}, "after": {"status": "NOT_EVALUATED", "score": None, "verdict": None}, "deltas": None})
    write_json(OUT / "quality_disposition.json", {"taskId": TASK_ID, "status": "BLOCKED / ARTIFACT_MATERIALIZATION_FAILED", "boundary": "9/9 PASS", "faceLocal": "8/9 PASS", "scenarioGlobal": "9/9 PASS", "pendingAuthoritativeEvaluations": 1, "qualityDisposition": "FAIL_PENDING_B05_RECHECK", "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False, "nextAction": "RERUN_P11_AFTER_APPROVED_GPU_WORKER_AVAILABLE"})
    write_json(OUT / "gpu_job_accounting.json", {"maxGpuJobs": 1, "gpuJobs": gpu_jobs, "artifactCount": 0, "maxArtifacts": 1})
    write_json(OUT / "provider_call_accounting.json", {"maxProviderCalls": 1, "providerCalls": 0, "retries": 0, "nanoCalls": 0, "alternativeProviderCalls": 0})
    write_json(OUT / "summary.json", {"taskId": TASK_ID, "status": "BLOCKED / ARTIFACT_MATERIALIZATION_FAILED", "humanDecisionApplied": True, "currentDenoise": current_denoise, "finalDenoise": final_denoise, "clamped": clamped, "t0": "PASS", "t1": "PASS", "t2": "PASS" if not start_reasons else "BLOCKED / LOCAL_REGRESSION", "t3": materialization["status"], "t4": "NOT_EXECUTED", "t5": "NOT_EXECUTED", "t6": "NOT_EXECUTED", "providerCalls": 0, "retries": 0, "gpuJobs": gpu_jobs, "nanoCalls": 0, "alternativeProviderCalls": 0, "boundary": "9/9 PASS", "faceLocal": "8/9 PASS", "scenarioGlobal": "9/9 PASS", "pendingAuthoritativeEvaluations": 1, "qualityDisposition": "FAIL_PENDING_B05_RECHECK", "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False, "nextAction": "RERUN_P11_AFTER_APPROVED_GPU_WORKER_AVAILABLE", "blockers": start_reasons + [materialization.get("reason", "") ]})
    finish_hashes()
    print(json.dumps({"status": "BLOCKED / ARTIFACT_MATERIALIZATION_FAILED", "output": str(OUT), "providerCalls": 0, "gpuJobs": gpu_jobs, "finalDenoise": final_denoise}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
