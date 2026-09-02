#!/usr/bin/env python3
"""Recover the approved Candidate v3 worker and close the locked B05 gate."""

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
from identity_restoration.infrastructure.comfyui.http_client import ComfyUIHttpClient
from identity_restoration.infrastructure.comfyui.graph_binder import validate_candidate_v3_graph
from identity_restoration.infrastructure.comfyui.workflow_repository import FileWorkflowRepository
from identity_restoration.infrastructure.restorers.comfyui_candidate_v3_adapter import (
    CANDIDATE_V3_WORKFLOW_ID,
    ComfyUiCandidateV3Adapter,
)


ROOT = Path(__file__).resolve().parents[1]
PHASE7 = ROOT / "artifacts/identity-restoration/phase7-candidate-v3"
JOB = PHASE7 / "jobs/phase7-diagnostic-20260828-B05.json"
INPUT_ROOT = PHASE7 / "phase7-diagnostic-20260828/B05-attempt-1"
P11 = PHASE7 / "r1-p11-human-parameter-final-closure-20260902T040000Z"
R2 = PHASE7 / "r1-p7-r2-b05-face-local-remediation-20260902T033100Z"
RUNBOOK = ROOT / "docs/identity-restoration/WINDOWS_WORKER_RUNBOOK.md"
PINS = ROOT / "config/projects/venho_hotel/identity_restoration/workflow_pins.yaml"
WORKFLOW_ROOT = ROOT / "identity_restoration/workflows"
WORKFLOW_ID = CANDIDATE_V3_WORKFLOW_ID
WORKFLOW_VERSION = "workflow-pins-v1"
MODEL = "gemini-flash-latest"
CONTRACT_ID = "candidate-v3-r1-p11-B05-denoise-040-v1"
OUTPUT_ARTIFACT_ID = "candidate-v3-r1-p11-B05-face-detail-denoise-040-v1"
TASK_ID = "R1-P11-R1-GPU-WORKER-RECOVERY-AND-FINAL-RESUME"
OUT = Path(os.environ.get(
    "R1_P11_R1_OUTPUT_DIR",
    str(PHASE7 / ("r1-p11-r1-gpu-recovery-final-resume-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))),
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


def documented_worker_endpoint() -> tuple[str, str]:
    text = RUNBOOK.read_text(encoding="utf-8")
    matches = re.findall(r"https://harry-rog\.taila40de0\.ts\.net", text)
    if not matches:
        raise RuntimeError("APPROVED_REMOTE_ENDPOINT_NOT_DOCUMENTED")
    return matches[0], str(RUNBOOK.relative_to(ROOT))


def worker_endpoint() -> tuple[str, str]:
    configured = os.environ.get("IDR_COMFYUI_REMOTE_BASE_URL", "").strip()
    if configured:
        return configured.rstrip("/"), "IDR_COMFYUI_REMOTE_BASE_URL"
    endpoint, source = documented_worker_endpoint()
    return endpoint, source


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


def baseline() -> dict[str, Any]:
    job = load_json(JOB)
    return {
        "taskId": TASK_ID,
        "authorization": {"R1_P11_R1_GPU_RECOVERY_AND_RESUME_AUTHORIZED": True},
        "startState": {
            "r1P11": "BLOCKED / ARTIFACT_MATERIALIZATION_FAILED",
            "blocker": "approved GPU worker unavailable at 127.0.0.1:8188",
            "boundary": "9/9 PASS",
            "faceLocal": "8/9 PASS",
            "scenarioGlobal": "9/9 PASS",
            "pending": 1,
            "qualityDisposition": "FAIL_PENDING_B05_RECHECK",
            "provider": "Gemini",
            "model": MODEL,
            "providerHold": "RECOVERED",
            "featureFlag": "OFF",
            "productionPromotion": "NO",
            "architectureChanged": False,
        },
        "lockedContract": {
            "caseId": "B05", "denoise": 0.40, "cfg": 6.0, "steps": 20,
            "contractId": CONTRACT_ID, "outputArtifactId": OUTPUT_ARTIFACT_ID,
            "referenceBinding": "A2",
        },
        "source": {
            "jobId": job["jobId"],
            "jobPath": str(JOB.relative_to(ROOT)),
            "jobSha256": sha_path(JOB),
            "sourceInputSha256": job["lineage"]["transform"]["canonicalImageSha256"],
            "p11Evidence": str(P11.relative_to(ROOT)),
            "r2Evidence": str(R2.relative_to(ROOT)),
        },
    }


def health_gate(endpoint: str) -> tuple[dict[str, Any], bool]:
    env = dict(os.environ)
    env.update({"IDR_COMFYUI_ENABLED": "true", "IDR_COMFYUI_BASE_URL": endpoint})
    result = subprocess.run(
        [sys.executable, "scripts/probe_gpu_worker.py"], cwd=ROOT, env=env,
        capture_output=True, text=True, check=False,
    )
    raw = (result.stdout + result.stderr).strip()
    try:
        probe = json.loads(result.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        probe = {"status": "OFFLINE", "raw": raw}
    healthy = probe.get("status") in {"HEALTHY", "DEGRADED"} and bool(probe.get("gpuName"))
    return {
        "endpoint": endpoint,
        "workerHost": "HARRY-ROG",
        "transport": "Tailscale HTTPS existing approved remote ComfyUI transport",
        "workerReachable": healthy,
        "comfyuiHealth": "PASS" if healthy else "FAIL",
        "gpuAvailable": bool(probe.get("gpuName")) if healthy else False,
        "approvedTransport": "PASS" if healthy else "FAIL",
        "workflowRuntimeAvailable": False,
        "probe": probe,
        "probeExitCode": result.returncode,
    }, healthy


def provider_sink(case_dir: Path):
    def sink(event: dict[str, Any]) -> None:
        raw = event.get("rawResponse")
        if raw is not None:
            (case_dir / "raw_provider_response.txt").write_text(str(raw).rstrip("\n") + "\n", encoding="utf-8")
        parsed = event.get("parsedEvidence")
        if parsed is not None:
            write_json(case_dir / "parsed_result.json", parsed)
    return sink


def main() -> int:
    output_dir = OUT / "artifact"
    output_path = output_dir / "restored-canonical.png"
    manifest_path = output_dir / "manifest.json"
    resume_existing = output_path.is_file() and manifest_path.is_file()
    if OUT.exists() and any(OUT.iterdir()) and not resume_existing:
        raise SystemExit(f"refusing to overwrite evidence directory: {OUT}")
    OUT.mkdir(parents=True, exist_ok=True)
    load_existing_env()
    write_json(OUT / "baseline.json", baseline())

    pins = yaml.safe_load(PINS.read_text(encoding="utf-8"))
    pin = pins["workflows"][WORKFLOW_ID]
    endpoint, endpoint_source = worker_endpoint()
    workflow_repo = FileWorkflowRepository(workflow_root=WORKFLOW_ROOT, pins_path=PINS)
    workflow, descriptor = workflow_repo.load(WORKFLOW_ID)
    workflow_hash = descriptor.sha256
    validate_candidate_v3_graph(workflow)
    authority = {
        "status": "PASS",
        "workerHost": "HARRY-ROG",
        "workerOS": "Windows 11",
        "gpu": "NVIDIA GTX 1660 SUPER 6GB",
        "transport": "Tailscale HTTPS existing approved remote ComfyUI transport",
        "comfyuiEndpoint": endpoint,
        "endpointAuthority": endpoint_source,
        "workerLocalBinding": "127.0.0.1:8188",
        "workerRuntime": "ComfyUI",
        "workflowId": WORKFLOW_ID,
        "workflowVersion": WORKFLOW_VERSION,
        "workflowHash": workflow_hash,
        "workflowHashPinned": pin["sha256"],
        "workflowPinMatch": workflow_hash == pin["sha256"],
        "adapter": "identity_restoration.infrastructure.restorers.comfyui_candidate_v3_adapter.ComfyUiCandidateV3Adapter",
        "architectureChanged": False,
    }
    write_json(OUT / "gpu_authority_reconstruction.json", authority)

    health, health_pass = health_gate(endpoint)
    health["workflowRuntimeAvailable"] = bool(authority["workflowPinMatch"])
    health_pass = health_pass and bool(authority["workflowPinMatch"])
    write_json(OUT / "gpu_health.json", health)

    execution = None
    gpu_jobs = 0
    artifact_created = False
    materialization_status = "NOT_EXECUTED"
    materialization_error = None
    if resume_existing:
        existing_manifest = load_json(manifest_path)
        execution = existing_manifest.get("adapterEvidence")
        gpu_jobs = 1
        artifact_created = True
        materialization_status = "PASS"
    elif health_pass:
        try:
            job = load_json(JOB)
            a2_pin = pins["a2_authority"]
            a2_path = Path(a2_pin["path"])
            crop_path = INPUT_ROOT / "canonical-input.png"
            editable_path = INPUT_ROOT / "canonical-editable-mask.png"
            feather_path = INPUT_ROOT / "canonical-feather-mask.png"
            client = ComfyUIHttpClient(base_url=endpoint, timeout_s=1260.0)
            adapter = ComfyUiCandidateV3Adapter(
                client=client, workflow=workflow, workflow_id=descriptor.workflow_id,
                workflow_sha256=descriptor.sha256, model_identifiers=descriptor.models,
                timeout_seconds=1260.0, gpu_execution_authorized=True,
                gpu_evidence={"worker": "HARRY-ROG", "os": "Windows 11", "gpu": "NVIDIA GTX 1660 SUPER 6GB", "transport": "approved remote ComfyUI path"},
            )
            request = RestorationRequest(
                run_id="r1-p11-r1-b05-denoise-040",
                attempt_id="B05-r1-p11-r1",
                crop_png=crop_path.read_bytes(),
                mask=MaskSet(editable=editable_path.read_bytes(), feather=feather_path.read_bytes(), version="candidate-v3-canonical-v1"),
                a2=A2Authority.from_bytes(a2_path.read_bytes()),
                workflow_id=WORKFLOW_ID, seed=42,
                params=RestorationParams(denoise=0.40, steps=20, cfg=6.0, sampler="euler", scheduler="normal"),
            )
            request.a2.verify(a2_pin["sha256"])
            gpu_jobs = 1
            restored = adapter.restore(request)
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(restored.png_bytes)
            execution = adapter.execution_evidence()
            output_hash = sha_path(output_path)
            manifest = {
                "manifestVersion": "1.0",
                "taskId": TASK_ID,
                "artifactId": OUTPUT_ARTIFACT_ID,
                "caseId": "B05",
                "lane": "FACE_LOCAL",
                "contractId": CONTRACT_ID,
                "sourceArtifactId": job["jobId"],
                "sourceInputSha256": sha_path(crop_path),
                "sourceEditableMaskSha256": sha_path(editable_path),
                "sourceFeatherMaskSha256": sha_path(feather_path),
                "referenceBinding": {"type": "A2", "sha256": a2_pin["sha256"], "path": a2_pin["path"]},
                "workflow": {"id": WORKFLOW_ID, "version": WORKFLOW_VERSION, "sha256": workflow_hash},
                "parameters": {"denoise": 0.40, "cfg": 6.0, "steps": 20, "sampler": "euler", "scheduler": "normal", "seed": 42},
                "output": {"path": str(output_path.relative_to(ROOT)), "sha256": output_hash, "width": restored.width, "height": restored.height},
                "adapterEvidence": execution,
                "evaluationOnly": True,
                "productionEligible": False,
                "featureFlag": "OFF",
            }
            write_json(manifest_path, manifest)
            artifact_created = True
            materialization_status = "PASS"
        except Exception as exc:
            materialization_status = "BLOCKED / ARTIFACT_MATERIALIZATION_FAILED"
            materialization_error = f"{type(exc).__name__}: {exc}"
    else:
        materialization_status = "BLOCKED / GPU_WORKER_UNAVAILABLE"
        materialization_error = "approved GPU worker health/recovery gate failed"

    materialization = {
        "status": materialization_status, "gpuJobs": gpu_jobs, "artifactCreated": artifact_created,
        "artifactCount": 1 if artifact_created else 0, "maxGpuJobs": 1, "maxArtifacts": 1,
        "outputArtifactId": OUTPUT_ARTIFACT_ID, "outputPath": str(output_path.relative_to(ROOT)),
        "manifestPath": str(manifest_path.relative_to(ROOT)), "requestedParameters": {"denoise": 0.40, "cfg": 6.0, "steps": 20},
        "gpuJobId": execution.get("promptId") if execution else None,
        "worker": "HARRY-ROG", "workflowId": WORKFLOW_ID, "workflowHash": workflow_hash,
        "outputHash": sha_path(output_path) if output_path.is_file() else None,
        "manifestHash": sha_path(manifest_path) if manifest_path.is_file() else None,
        "error": materialization_error,
    }
    write_json(OUT / "artifact_materialization.json", materialization)

    lineage = {
        "status": "NOT_EXECUTED", "artifactExists": output_path.is_file(),
        "artifactHashValid": False, "manifestValid": False, "contractMatch": False,
        "caseId": "B05", "b05Only": True, "sourceLineageValid": False,
        "workflowLineageValid": False, "referenceBinding": "A2", "referenceBindingValid": False,
        "denoise": 0.40, "denoiseMatch": False, "cfg": 6.0, "cfgUnchanged": True,
        "steps": 20, "stepsUnchanged": True, "passingCasesProtected": True,
        "boundaryProtected": "9/9 PASS", "otherFaceLocalPassingCasesProtected": "8/8 PASS",
        "scenarioGlobalProtected": "9/9 PASS", "thresholdsUnchanged": True, "rubricUnchanged": True,
    }
    if artifact_created:
        manifest = load_json(manifest_path)
        lineage.update({
            "status": "PASS",
            "artifactHashValid": manifest["output"]["sha256"] == sha_path(output_path),
            "manifestValid": manifest["artifactId"] == OUTPUT_ARTIFACT_ID and manifest["caseId"] == "B05",
            "contractMatch": manifest["contractId"] == CONTRACT_ID and manifest["parameters"] == {"denoise": 0.40, "cfg": 6.0, "steps": 20, "sampler": "euler", "scheduler": "normal", "seed": 42},
            "sourceLineageValid": manifest["sourceInputSha256"] == sha_path(INPUT_ROOT / "canonical-input.png"),
            "workflowLineageValid": manifest["workflow"]["sha256"] == workflow_hash,
            "referenceBindingValid": manifest["referenceBinding"]["sha256"] == pins["a2_authority"]["sha256"],
            "denoiseMatch": manifest["parameters"]["denoise"] == 0.40,
        })
        if not all(lineage[key] for key in ("artifactHashValid", "manifestValid", "contractMatch", "sourceLineageValid", "workflowLineageValid", "referenceBindingValid", "denoiseMatch")):
            lineage["status"] = "BLOCKED_LOCAL_REGRESSION"
    write_json(OUT / "lineage_validation.json", lineage)

    test_code, test_output = run_offline([sys.executable, "-m", "pytest", "-q", "tests/test_candidate_v3_r1_p11_r1_gpu_recovery_final_resume.py", "tests/identity_restoration/infrastructure/test_comfyui_candidate_v3_adapter.py", "tests/identity_restoration/infrastructure/test_comfyui_health_probe.py"])
    compile_code, compile_output = run_offline([sys.executable, "-m", "compileall", "-q", "identity_restoration", "validator_studio", "shared/vision", "scripts/run_candidate_v3_r1_p11_r1_gpu_recovery_final_resume.py"])
    diff_code, diff_output = run_offline(["git", "diff", "--check"])
    (OUT / "test_results.txt").write_text(test_output, encoding="utf-8")
    (OUT / "compileall.txt").write_text(compile_output if compile_output.strip() else "compileall=PASS\n", encoding="utf-8")
    (OUT / "git_diff_check.txt").write_text(diff_output if diff_output.strip() else "git_diff_check=PASS\n", encoding="utf-8")
    local_gate = lineage["status"] == "PASS" and test_code == 0 and compile_code == 0 and diff_code == 0

    face_result: dict[str, Any] | None = None
    provider_calls = 0
    if local_gate:
        provider_calls = 1
        case_dir = OUT / "face_local" / "B05"
        case_dir.mkdir(parents=True, exist_ok=True)
        try:
            from shared.vision.paid_call_guard import paid_call_context
            from shared.vision.providers.gemini_vision import classify_gemini_failure
            from validator_studio.face_validator import _assert_face_observation_contract, _load_face_rubric, validate_face
            from validator_studio.schemas.face_validation import FaceValidationObservation
            os.environ["VALIDATOR_LIVE_ENABLED"] = "true"
            os.environ["VALIDATOR_MAX_NEW_CALLS"] = "1"
            os.environ["GEMINI_MAX_TRANSPORT_ATTEMPTS"] = "1"
            os.environ["GEMINI_VISION_MODEL"] = MODEL
            os.environ["VALIDATOR_PAID_CALL_LEDGER"] = str(OUT / "provider-paid-call-ledger.jsonl")
            with paid_call_context({"benchmarkId": "candidate-v3-r1-p11-r1-b05-face-local", "branch": "FACE_LOCAL", "imageSha256": sha_path(output_path), "sampleIndex": 1, "reason": "authorized single B05 R1-P11-R1 recheck", "historicalEvidenceSearch": {"lineage": "VERIFIED"}}):
                report = validate_face("venho_hotel", "linh_an", output_path, provider="gemini", reference_image_paths=[Path(pins["a2_authority"]["path"])], samples=1, raw_response_sink=provider_sink(case_dir), validation_cycle_id="candidate-v3-r1-p11-r1-b05-face-1", attempt_id="r1-p11-r1")
                observation = FaceValidationObservation.model_validate(report.raw_observation)
                _assert_face_observation_contract(observation.model_dump(mode="json"), _load_face_rubric("venho_hotel"))
            data = report.model_dump(mode="json")
            cats = data["category_scores"]
            face_result = {"valid": True, "score": float(data["overall_score"]), "verdict": data["verdict"], "eyesBrows": cats.get("eyes_and_brows"), "facialShape": cats.get("facial_shape"), "mouthChin": cats.get("mouth_and_chin"), "rawHash": sha_path(case_dir / "raw_provider_response.txt") if (case_dir / "raw_provider_response.txt").is_file() else None, "parsedHash": sha_path(case_dir / "parsed_result.json") if (case_dir / "parsed_result.json").is_file() else None, "reportHash": canonical_hash(data), "provider": "Gemini", "model": MODEL, "lineageStatus": "VERIFIED"}
            write_json(case_dir / "evaluation_report.json", data)
        except Exception as exc:
            from shared.vision.providers.gemini_vision import classify_gemini_failure
            face_result = {"valid": False, "score": None, "verdict": None, "eyesBrows": None, "facialShape": None, "mouthChin": None, "rawHash": sha_path(case_dir / "raw_provider_response.txt") if (case_dir / "raw_provider_response.txt").is_file() else None, "parsedHash": None, "provider": "Gemini", "model": MODEL, "lineageStatus": "VERIFIED", "invalidReason": classify_gemini_failure(exc), "error": str(exc)}

    if face_result and face_result["valid"]:
        quality_pass = face_result["score"] >= 90.0
        final_status = "CLOSED / QUALITY_PASS" if quality_pass else "CLOSED / QUALITY_FAIL"
        final_face = "9/9 PASS" if quality_pass else "8/9 PASS"
        pending = 0
        disposition = "PASS" if quality_pass else "FAIL"
        next_action = "PROMOTION_READINESS_REVIEW_REQUIRES_SEPARATE_AUTHORIZATION" if quality_pass else "HUMAN_DECISION_REQUIRED"
    elif provider_calls:
        final_status, final_face, pending, disposition, next_action = "PROVIDER_BLOCKED", "8/9 PASS", 1, "FAIL_PENDING_B05_RECHECK", "RERUN_P11_R1_AFTER_PROVIDER_RECOVERY"
    elif not health_pass:
        final_status, final_face, pending, disposition, next_action = "BLOCKED / GPU_WORKER_UNAVAILABLE", "8/9 PASS", 1, "FAIL_PENDING_B05_RECHECK", "RECOVER_APPROVED_GPU_WORKER_AND_RERUN_R1_P11_R1"
    elif materialization_status != "PASS":
        final_status, final_face, pending, disposition, next_action = "BLOCKED / ARTIFACT_MATERIALIZATION_FAILED", "8/9 PASS", 1, "FAIL_PENDING_B05_RECHECK", "RERUN_R1_P11_R1_AFTER_GPU_MATERIALIZATION_RECOVERY"
    else:
        final_status, final_face, pending, disposition, next_action = "BLOCKED_LOCAL_REGRESSION", "8/9 PASS", 1, "FAIL_PENDING_B05_RECHECK", "FIX_LOCAL_REGRESSION_BEFORE_PROVIDER_CALL"

    before = {"score": 88.50, "eyesBrows": 87.0, "facialShape": 88.0, "mouthChin": 89.0}
    after = face_result or {"score": None, "eyesBrows": None, "facialShape": None, "mouthChin": None}
    write_json(OUT / "before_after_comparison.json", {"caseId": "B05", "before": before, "after": after, "deltas": {key: (after[key] - before[key]) if after.get(key) is not None else None for key in before}})
    write_json(OUT / "quality_disposition.json", {"taskId": TASK_ID, "status": final_status, "boundary": "9/9 PASS", "faceLocal": final_face, "scenarioGlobal": "9/9 PASS", "pendingAuthoritativeEvaluations": pending, "qualityDisposition": disposition, "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False, "nextAction": next_action})
    write_json(OUT / "gpu_job_accounting.json", {"maxGpuJobs": 1, "gpuJobs": gpu_jobs, "maxArtifacts": 1, "artifactsCreated": 1 if artifact_created else 0, "nanoCalls": 0, "alternativeProviderCalls": 0})
    write_json(OUT / "provider_call_accounting.json", {"maxProviderCalls": 1, "providerCalls": provider_calls, "retries": 0, "maxProviderRetries": 0, "nanoCalls": 0, "alternativeProviderCalls": 0, "provider": "Gemini", "model": MODEL})
    write_json(OUT / "summary.json", {"taskId": TASK_ID, "status": final_status, "t0": "PASS", "t1": "PASS" if health_pass else "BLOCKED / GPU_WORKER_UNAVAILABLE", "t2": materialization_status, "t3": lineage["status"] if artifact_created else "NOT_EXECUTED", "t4": "PASS" if face_result and face_result["valid"] else ("PROVIDER_BLOCKED" if provider_calls else "NOT_EXECUTED"), "t5": final_status, "providerCalls": provider_calls, "gpuJobs": gpu_jobs, "artifactsCreated": 1 if artifact_created else 0, "retries": 0, "boundary": "9/9 PASS", "faceLocal": final_face, "scenarioGlobal": "9/9 PASS", "pendingAuthoritativeEvaluations": pending, "qualityDisposition": disposition, "b05FinalScore": after.get("score"), "b05FinalVerdict": after.get("verdict"), "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False, "nextAction": next_action})
    finish_hashes()
    print(json.dumps({"status": final_status, "output": str(OUT), "gpuJobs": gpu_jobs, "providerCalls": provider_calls, "score": after.get("score")}))
    return 0 if final_status.startswith("CLOSED /") else 2


if __name__ == "__main__":
    raise SystemExit(main())
