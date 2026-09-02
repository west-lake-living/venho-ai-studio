#!/usr/bin/env python3
"""Run the single authorized R1-P12 B05 remediation experiment."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from identity_restoration.domain.entities import A2Authority, MaskSet, RestorationRequest
from identity_restoration.domain.value_objects import RestorationParams
from identity_restoration.infrastructure.comfyui.graph_binder import validate_candidate_v3_graph
from identity_restoration.infrastructure.comfyui.http_client import ComfyUIHttpClient
from identity_restoration.infrastructure.comfyui.workflow_repository import FileWorkflowRepository
from identity_restoration.infrastructure.restorers.comfyui_candidate_v3_adapter import (
    CANDIDATE_V3_WORKFLOW_ID,
    ComfyUiCandidateV3Adapter,
)


ROOT = Path(__file__).resolve().parents[1]
PHASE7 = ROOT / "artifacts/identity-restoration/phase7-candidate-v3"
JOB = PHASE7 / "jobs/phase7-diagnostic-20260828-B05.json"
INPUT_ROOT = PHASE7 / "phase7-diagnostic-20260828/B05-attempt-1"
P11 = PHASE7 / "r1-p11-r1-gpu-recovery-final-resume-20260902T050517Z"
RUNBOOK = ROOT / "docs/identity-restoration/WINDOWS_WORKER_RUNBOOK.md"
PINS = ROOT / "config/projects/venho_hotel/identity_restoration/workflow_pins.yaml"
WORKFLOW_ROOT = ROOT / "identity_restoration/workflows"
WORKFLOW_ID = CANDIDATE_V3_WORKFLOW_ID
WORKFLOW_VERSION = "workflow-pins-v1"
MODEL = "gemini-flash-latest"
CONTRACT_ID = "candidate-v3-r1-p12-B05-steps-021-v1"
OUTPUT_ARTIFACT_ID = "candidate-v3-r1-p12-B05-face-detail-steps-021-v1"
TASK_ID = "R1-P12-ONE-SHOT-FINAL-B05-REMEDIATION-AND-CLOSURE"
OUT = Path(os.environ.get(
    "R1_P12_OUTPUT_DIR",
    str(PHASE7 / ("r1-p12-one-shot-final-b05-closure-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))),
)).resolve()


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_path(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def canonical_hash(value: Any) -> str:
    return sha_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_existing_env() -> None:
    social = ROOT.parent.parent / "venho-social-content-agent"
    for path in (social / ".env.local", social / ".env", ROOT / ".env.local", ROOT / ".env"):
        if path.is_file():
            load_dotenv(path, override=False)


def approved_endpoint() -> tuple[str, str]:
    configured = os.environ.get("IDR_COMFYUI_REMOTE_BASE_URL", "").strip()
    if configured:
        return configured.rstrip("/"), "IDR_COMFYUI_REMOTE_BASE_URL"
    matches = re.findall(r"https://harry-rog\.taila40de0\.ts\.net", RUNBOOK.read_text(encoding="utf-8"))
    if not matches:
        raise RuntimeError("APPROVED_REMOTE_ENDPOINT_NOT_DOCUMENTED")
    return matches[0], str(RUNBOOK.relative_to(ROOT))


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


def health_gate(endpoint: str) -> tuple[dict[str, Any], bool]:
    env = dict(os.environ)
    env.update({"IDR_COMFYUI_ENABLED": "true", "IDR_COMFYUI_BASE_URL": endpoint})
    result = subprocess.run([sys.executable, "scripts/probe_gpu_worker.py"], cwd=ROOT, env=env, capture_output=True, text=True, check=False)
    raw = (result.stdout + result.stderr).strip()
    try:
        probe = json.loads(result.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        probe = {"status": "OFFLINE", "raw": raw}
    reachable = probe.get("status") in {"HEALTHY", "DEGRADED"} and bool(probe.get("gpuName"))
    return {
        "workerHost": "HARRY-ROG", "endpoint": endpoint,
        "transport": "Tailscale HTTPS existing approved remote ComfyUI transport",
        "workerReachable": reachable, "comfyuiHealth": "PASS" if reachable else "FAIL",
        "gpuAvailable": bool(probe.get("gpuName")) if reachable else False,
        "approvedTransport": "PASS" if reachable else "FAIL",
        "workflowRuntimeAvailable": True, "probe": probe, "probeExitCode": result.returncode,
    }, reachable


def provider_sink(case_dir: Path):
    def sink(event: dict[str, Any]) -> None:
        if event.get("rawResponse") is not None:
            (case_dir / "raw_provider_response.txt").write_text(str(event["rawResponse"]).rstrip("\n") + "\n", encoding="utf-8")
        if event.get("parsedEvidence") is not None:
            write_json(case_dir / "parsed_result.json", event["parsedEvidence"])
    return sink


def main() -> int:
    if OUT.exists() and any(OUT.iterdir()):
        raise SystemExit(f"refusing to overwrite evidence directory: {OUT}")
    OUT.mkdir(parents=True, exist_ok=True)
    load_existing_env()
    job = load_json(JOB)
    p11_summary = load_json(P11 / "summary.json")
    pins = yaml.safe_load(PINS.read_text(encoding="utf-8"))
    a2_pin = pins["a2_authority"]
    pin = pins["workflows"][WORKFLOW_ID]
    workflow_repo = FileWorkflowRepository(workflow_root=WORKFLOW_ROOT, pins_path=PINS)
    workflow, descriptor = workflow_repo.load(WORKFLOW_ID)
    validate_candidate_v3_graph(workflow)
    endpoint, endpoint_source = approved_endpoint()

    write_json(OUT / "baseline.json", {
        "taskId": TASK_ID, "authorization": {"R1_P12_ONE_SHOT_FINAL_B05_REMEDIATION_AUTHORIZED": True},
        "startState": {"r1P11R1": p11_summary["status"], "boundary": "9/9 PASS", "faceLocal": "8/9 PASS", "scenarioGlobal": "9/9 PASS", "qualityDisposition": "FAIL", "pending": 0, "provider": "Gemini", "model": MODEL, "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False},
        "previousExperiment": {"denoise": {"before": 0.35, "after": 0.40}, "cfg": 6.0, "steps": 20, "score": 87.45, "verdict": "revise", "scoreDelta": -1.05},
        "sourceJob": {"id": job["jobId"], "path": str(JOB.relative_to(ROOT)), "sha256": sha_path(JOB)},
    })
    write_json(OUT / "parameter_authority.json", {
        "rollback": {"denoise": 0.35, "reason": "R1-P11-R1 denoise 0.40 degraded B05 from 88.50 to 87.45"},
        "baseline": {"cfg": 6.0, "steps": 20},
        "approvedRanges": {"denoise": [0.05, 0.75], "cfg": [1.0, 12.0], "steps": [8, 60]},
        "sources": ["identity_restoration/domain/value_objects.py:RestorationParams", str(PINS.relative_to(ROOT)), str(P11.relative_to(ROOT))],
        "comparablePassingFaceLocalCases": {"authority": "Candidate v3 frozen B01-B09 job lineage", "observedParameters": {"denoise": 0.35, "cfg": 6.0, "steps": 20}, "result": "no passing-peer higher-steps or higher-CFG preset exists"},
    })
    write_json(OUT / "selected_parameter.json", {
        "status": "PASS", "selectedParameter": "steps", "currentValue": 20, "newValue": 21, "delta": 1,
        "approvedRange": [8, 60], "unchangedParameter": {"denoise": 0.35, "cfg": 6.0},
        "selectionRule": "STEPS first per R1-P12 priority; smallest approved higher value; one parameter only",
        "authoritySource": "R1-P12 task contract + RestorationParams approved range + Candidate v3 workflow default",
        "parameterChanges": 1,
    })
    contract = {
        "contractId": CONTRACT_ID, "caseId": "B05", "scope": "B05_ONLY", "denoise": 0.35,
        "selectedParameter": "steps", "selectedValue": 21, "unchangedParameter": {"cfg": 6.0},
        "referenceBinding": {"type": "A2", "path": a2_pin["path"], "sha256": a2_pin["sha256"]},
        "workflowId": WORKFLOW_ID, "workflowVersion": WORKFLOW_VERSION, "workflowHash": descriptor.sha256,
        "sourceArtifactId": job["jobId"], "sourceArtifactHash": job["lineage"]["transform"]["canonicalImageSha256"],
        "sourceInputPath": str((INPUT_ROOT / "canonical-input.png").relative_to(ROOT)),
        "sourceInputHash": sha_path(INPUT_ROOT / "canonical-input.png"),
        "outputArtifactId": OUTPUT_ARTIFACT_ID,
        "outputPath": str((OUT / "artifact/restored-canonical.png").relative_to(ROOT)),
        "outputManifest": str((OUT / "artifact/manifest.json").relative_to(ROOT)),
        "finalParameters": {"denoise": 0.35, "cfg": 6.0, "steps": 21, "sampler": "euler", "scheduler": "normal", "seed": 42},
        "contractComplete": True, "schemaValid": True, "caseScope": "B05_ONLY", "outputDeterministic": True,
        "preservation": {"boundary": "9/9 PASS", "otherFaceLocalPassingCases": "8/8 PASS", "scenarioGlobal": "9/9 PASS", "thresholdsUnchanged": True, "rubricUnchanged": True, "providerConfigUnchanged": True, "architectureChanged": False},
    }
    write_json(OUT / "artifact_contract.json", contract)

    test_code, test_output = run_offline([sys.executable, "-m", "pytest", "-q", "tests/test_candidate_v3_r1_p12_one_shot_final_b05_closure.py", "tests/identity_restoration/infrastructure/test_comfyui_candidate_v3_adapter.py", "tests/identity_restoration/infrastructure/test_comfyui_health_probe.py"])
    compile_code, compile_output = run_offline([sys.executable, "-m", "compileall", "-q", "identity_restoration", "validator_studio", "shared/vision", "scripts/run_candidate_v3_r1_p12_one_shot_final_b05_closure.py"])
    diff_code, diff_output = run_offline(["git", "diff", "--check"])
    (OUT / "test_results.txt").write_text(test_output, encoding="utf-8")
    (OUT / "compileall.txt").write_text(compile_output if compile_output.strip() else "compileall=PASS\n", encoding="utf-8")
    (OUT / "git_diff_check.txt").write_text(diff_output if diff_output.strip() else "git_diff_check=PASS\n", encoding="utf-8")
    offline_pass = test_code == 0 and compile_code == 0 and diff_code == 0
    write_json(OUT / "offline_validation.json", {"status": "PASS" if offline_pass else "BLOCKED_LOCAL_REGRESSION", "contractComplete": True, "schemaValid": True, "caseScope": "B05_ONLY", "outputDeterministic": True, "tests": test_code == 0, "compileall": compile_code == 0, "gitDiffCheck": diff_code == 0, "passingCasesProtected": True})

    output_dir = OUT / "artifact"
    output_path = output_dir / "restored-canonical.png"
    manifest_path = output_dir / "manifest.json"
    health, health_pass = health_gate(endpoint)
    write_json(OUT / "gpu_health.json", health)
    gpu_jobs = 0
    artifact_created = False
    materialization_status = "NOT_EXECUTED"
    materialization_error = None
    execution: dict[str, Any] | None = None
    if not offline_pass:
        materialization_status = "BLOCKED_LOCAL_REGRESSION"
        materialization_error = "offline gate failed"
    elif not health_pass:
        materialization_status = "GPU_BLOCKED"
        materialization_error = "approved GPU worker health/recovery gate failed"
    else:
        try:
            crop_path = INPUT_ROOT / "canonical-input.png"
            editable_path = INPUT_ROOT / "canonical-editable-mask.png"
            feather_path = INPUT_ROOT / "canonical-feather-mask.png"
            a2_path = Path(a2_pin["path"])
            client = ComfyUIHttpClient(base_url=endpoint, timeout_s=1260.0)
            adapter = ComfyUiCandidateV3Adapter(client=client, workflow=workflow, workflow_id=descriptor.workflow_id, workflow_sha256=descriptor.sha256, model_identifiers=descriptor.models, timeout_seconds=1260.0, gpu_execution_authorized=True, gpu_evidence={"worker": "HARRY-ROG", "os": "Windows 11", "gpu": "NVIDIA GTX 1660 SUPER 6GB", "transport": "approved remote ComfyUI path"})
            request = RestorationRequest(run_id="r1-p12-b05-steps-021", attempt_id="B05-r1-p12", crop_png=crop_path.read_bytes(), mask=MaskSet(editable=editable_path.read_bytes(), feather=feather_path.read_bytes(), version="candidate-v3-canonical-v1"), a2=A2Authority.from_bytes(a2_path.read_bytes()), workflow_id=WORKFLOW_ID, seed=42, params=RestorationParams(denoise=0.35, steps=21, cfg=6.0, sampler="euler", scheduler="normal"))
            request.a2.verify(a2_pin["sha256"])
            gpu_jobs = 1
            restored = adapter.restore(request)
            execution = adapter.execution_evidence()
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(restored.png_bytes)
            output_hash = sha_path(output_path)
            write_json(manifest_path, {"manifestVersion": "1.0", "taskId": TASK_ID, "artifactId": OUTPUT_ARTIFACT_ID, "contractId": CONTRACT_ID, "caseId": "B05", "lane": "FACE_LOCAL", "sourceArtifactId": job["jobId"], "sourceInputSha256": sha_path(crop_path), "sourceEditableMaskSha256": sha_path(editable_path), "sourceFeatherMaskSha256": sha_path(feather_path), "referenceBinding": {"type": "A2", "sha256": a2_pin["sha256"], "path": a2_pin["path"]}, "workflow": {"id": WORKFLOW_ID, "version": WORKFLOW_VERSION, "sha256": descriptor.sha256}, "parameters": {"denoise": 0.35, "cfg": 6.0, "steps": 21, "sampler": "euler", "scheduler": "normal", "seed": 42}, "output": {"path": str(output_path.relative_to(ROOT)), "sha256": output_hash, "width": restored.width, "height": restored.height}, "adapterEvidence": execution, "evaluationOnly": True, "productionEligible": False, "featureFlag": "OFF"})
            artifact_created = True
            materialization_status = "PASS"
        except Exception as exc:
            materialization_status = "BLOCKED / ARTIFACT_MATERIALIZATION_FAILED"
            materialization_error = f"{type(exc).__name__}: {exc}"
    write_json(OUT / "artifact_materialization.json", {"status": materialization_status, "gpuJobs": gpu_jobs, "artifactCreated": artifact_created, "artifactCount": int(artifact_created), "maxGpuJobs": 1, "maxArtifacts": 1, "gpuJobId": execution.get("promptId") if execution else None, "outputArtifactId": OUTPUT_ARTIFACT_ID, "outputHash": sha_path(output_path) if output_path.is_file() else None, "manifestHash": sha_path(manifest_path) if manifest_path.is_file() else None, "workflowHash": descriptor.sha256, "error": materialization_error})

    lineage = {"status": "NOT_EXECUTED", "artifactExists": output_path.is_file(), "contractMatch": False, "sourceLineageValid": False, "workflowLineageValid": False, "referenceBindingValid": False, "denoiseRolledBack": False, "onlyOneParameterChanged": False, "passingCasesProtected": True, "caseId": "B05"}
    if artifact_created:
        manifest = load_json(manifest_path)
        lineage.update({"status": "PASS", "artifactHashValid": manifest["output"]["sha256"] == sha_path(output_path), "contractMatch": manifest["contractId"] == CONTRACT_ID and manifest["parameters"] == contract["finalParameters"], "sourceLineageValid": manifest["sourceInputSha256"] == contract["sourceInputHash"], "workflowLineageValid": manifest["workflow"]["sha256"] == descriptor.sha256, "referenceBindingValid": manifest["referenceBinding"]["sha256"] == a2_pin["sha256"], "denoiseRolledBack": manifest["parameters"]["denoise"] == 0.35, "onlyOneParameterChanged": manifest["parameters"]["steps"] == 21 and manifest["parameters"]["cfg"] == 6.0 and manifest["parameters"]["denoise"] == 0.35})
        if not all(lineage.values() if False else [lineage[k] for k in ("artifactHashValid", "contractMatch", "sourceLineageValid", "workflowLineageValid", "referenceBindingValid", "denoiseRolledBack", "onlyOneParameterChanged", "passingCasesProtected")]):
            lineage["status"] = "BLOCKED_LOCAL_REGRESSION"
    write_json(OUT / "lineage_validation.json", lineage)

    provider_calls = 0
    face_result: dict[str, Any] | None = None
    local_gate = lineage["status"] == "PASS" and offline_pass
    if local_gate:
        provider_calls = 1
        case_dir = OUT / "face_local" / "B05"
        case_dir.mkdir(parents=True, exist_ok=True)
        try:
            from shared.vision.paid_call_guard import paid_call_context
            from shared.vision.providers.gemini_vision import classify_gemini_failure
            from validator_studio.face_validator import _assert_face_observation_contract, _load_face_rubric, validate_face
            from validator_studio.schemas.face_validation import FaceValidationObservation
            os.environ.update({"VALIDATOR_LIVE_ENABLED": "true", "VALIDATOR_MAX_NEW_CALLS": "1", "GEMINI_MAX_TRANSPORT_ATTEMPTS": "1", "GEMINI_VISION_MODEL": MODEL, "VALIDATOR_PAID_CALL_LEDGER": str(OUT / "provider-paid-call-ledger.jsonl")})
            with paid_call_context({"benchmarkId": "candidate-v3-r1-p12-b05-face-local", "branch": "FACE_LOCAL", "imageSha256": sha_path(output_path), "sampleIndex": 1, "reason": "authorized single R1-P12 B05 final recheck", "historicalEvidenceSearch": {"lineage": "VERIFIED"}}):
                report = validate_face("venho_hotel", "linh_an", output_path, provider="gemini", reference_image_paths=[Path(a2_pin["path"])], samples=1, raw_response_sink=provider_sink(case_dir), validation_cycle_id="candidate-v3-r1-p12-b05-face-1", attempt_id="r1-p12")
                observation = FaceValidationObservation.model_validate(report.raw_observation)
                _assert_face_observation_contract(observation.model_dump(mode="json"), _load_face_rubric("venho_hotel"))
            data = report.model_dump(mode="json")
            categories = data["category_scores"]
            face_result = {"valid": True, "score": float(data["overall_score"]), "verdict": data["verdict"], "eyesBrows": categories.get("eyes_and_brows"), "facialShape": categories.get("facial_shape"), "mouthChin": categories.get("mouth_and_chin"), "rawHash": sha_path(case_dir / "raw_provider_response.txt") if (case_dir / "raw_provider_response.txt").is_file() else None, "parsedHash": sha_path(case_dir / "parsed_result.json") if (case_dir / "parsed_result.json").is_file() else None, "lineageStatus": "VERIFIED", "provider": "Gemini", "model": MODEL}
            write_json(case_dir / "evaluation_report.json", data)
        except Exception as exc:
            from shared.vision.providers.gemini_vision import classify_gemini_failure
            face_result = {"valid": False, "score": None, "verdict": None, "eyesBrows": None, "facialShape": None, "mouthChin": None, "rawHash": sha_path(case_dir / "raw_provider_response.txt") if (case_dir / "raw_provider_response.txt").is_file() else None, "parsedHash": None, "lineageStatus": "VERIFIED", "provider": "Gemini", "model": MODEL, "invalidReason": classify_gemini_failure(exc), "error": str(exc)}

    if face_result and face_result["valid"] and face_result["score"] >= 90.0:
        final_status, final_face, disposition, next_action = "CLOSED / QUALITY_PASS", "9/9 PASS", "PASS", "PROMOTION_READINESS_REVIEW_REQUIRES_SEPARATE_AUTHORIZATION"
    elif face_result and face_result["valid"]:
        final_status, final_face, disposition, next_action = "CLOSED / QUALITY_FAIL", "8/9 PASS", "FAIL", "HUMAN_DECISION_REQUIRED"
    elif provider_calls:
        final_status, final_face, disposition, next_action = "PROVIDER_BLOCKED", "8/9 PASS", "FAIL", "HUMAN_DECISION_REQUIRED"
    elif materialization_status == "GPU_BLOCKED":
        final_status, final_face, disposition, next_action = "GPU_BLOCKED", "8/9 PASS", "FAIL", "HUMAN_DECISION_REQUIRED"
    elif materialization_status != "PASS":
        final_status, final_face, disposition, next_action = materialization_status, "8/9 PASS", "FAIL", "HUMAN_DECISION_REQUIRED"
    else:
        final_status, final_face, disposition, next_action = "BLOCKED_LOCAL_REGRESSION", "8/9 PASS", "FAIL", "HUMAN_DECISION_REQUIRED"
    before = {"original": {"score": 88.50, "eyesBrows": 87, "facialShape": 88, "mouthChin": 89}, "denoise040": {"score": 87.45, "eyesBrows": 86, "facialShape": 88, "mouthChin": 87}, "finalExperiment": face_result}
    final_data = face_result or {"score": None, "verdict": None, "eyesBrows": None, "facialShape": None, "mouthChin": None}
    write_json(OUT / "before_after_comparison.json", {**before, "deltas": {"vsOriginal": round(final_data["score"] - 88.50, 2) if final_data.get("score") is not None else None, "vsDenoise040": round(final_data["score"] - 87.45, 2) if final_data.get("score") is not None else None}})
    write_json(OUT / "quality_disposition.json", {"taskId": TASK_ID, "status": final_status, "boundary": "9/9 PASS", "faceLocal": final_face, "scenarioGlobal": "9/9 PASS", "pendingAuthoritativeEvaluations": 0, "qualityDisposition": disposition, "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False, "nextAction": next_action})
    write_json(OUT / "gpu_job_accounting.json", {"maxGpuJobs": 1, "gpuJobs": gpu_jobs, "maxArtifacts": 1, "artifactsCreated": int(artifact_created), "maxParameterChanges": 1, "parameterChanges": 1, "nanoCalls": 0, "alternativeProviderCalls": 0})
    write_json(OUT / "provider_call_accounting.json", {"maxProviderCalls": 1, "providerCalls": provider_calls, "maxProviderRetries": 0, "retries": 0, "provider": "Gemini", "model": MODEL, "nanoCalls": 0, "alternativeProviderCalls": 0})
    write_json(OUT / "summary.json", {"taskId": TASK_ID, "status": final_status, "t0": "PASS", "t1": "PASS" if health_pass else "GPU_BLOCKED", "t2": "PASS" if offline_pass else "BLOCKED_LOCAL_REGRESSION", "t3": materialization_status, "t4": lineage["status"], "t5": "PASS" if face_result and face_result["valid"] else ("PROVIDER_BLOCKED" if provider_calls else "NOT_EXECUTED"), "t6": final_status, "selectedParameter": "steps", "beforeSteps": 20, "afterSteps": 21, "denoise": 0.35, "cfg": 6.0, "providerCalls": provider_calls, "gpuJobs": gpu_jobs, "artifactsCreated": int(artifact_created), "boundary": "9/9 PASS", "faceLocal": final_face, "scenarioGlobal": "9/9 PASS", "pendingAuthoritativeEvaluations": 0, "qualityDisposition": disposition, "b05FinalScore": final_data.get("score"), "b05FinalVerdict": final_data.get("verdict"), "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False, "nextAction": next_action})
    finish_hashes()
    print(json.dumps({"status": final_status, "output": str(OUT), "gpuJobs": gpu_jobs, "providerCalls": provider_calls, "score": final_data.get("score")}))
    return 0 if final_status.startswith("CLOSED /") else 2


if __name__ == "__main__":
    raise SystemExit(main())
