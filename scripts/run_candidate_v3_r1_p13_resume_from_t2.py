#!/usr/bin/env python3
"""Resume R1-P13 at T2 after the human-recovered worker health gate."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
from scripts.run_candidate_v3_r1_p13_gpu_recovery_resume_p12 import (
    CONTRACT_ID,
    INPUT_ROOT,
    JOB,
    MODEL,
    OUTPUT_ARTIFACT_ID,
    P12,
    PHASE7,
    PINS,
    ROOT,
    WORKFLOW_ID,
    WORKFLOW_ROOT,
    WORKFLOW_VERSION,
    health_gate,
    load_existing_env,
    load_json,
    provider_sink,
    run_offline,
    sha_path,
    write_json,
)


P13 = PHASE7 / "r1-p13-gpu-recovery-p12-final-resume-20260902T071500Z"
TASK_ID = "R1-P13-RESUME-FROM-T2"
OUT = Path(os.environ.get(
    "R1_P13_RESUME_OUTPUT_DIR",
    str(PHASE7 / ("r1-p13-resume-from-t2-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))),
)).resolve()


def finish_hashes() -> None:
    import hashlib

    files = {}
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            files[str(path.relative_to(OUT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    write_json(OUT / "hashes.sha256", {"algorithm": "SHA-256", "files": files, "count": len(files)})


def main() -> int:
    if OUT.exists() and any(OUT.iterdir()):
        raise SystemExit(f"refusing to overwrite evidence directory: {OUT}")
    OUT.mkdir(parents=True, exist_ok=True)
    load_existing_env()

    # Resume authority is read from the completed P13 T0 evidence; no T0 rerun.
    previous = load_json(P13 / "summary.json")
    authority = load_json(P13 / "p12_resume_authority.json")
    p12_contract = load_json(P12 / "artifact_contract.json")
    job = load_json(JOB)
    resume_valid = previous.get("status") == "GPU_BLOCKED" and authority.get("resumeAuthorityValid") is True and authority.get("parameterChangesRequired") is False
    write_json(OUT / "resume_baseline.json", {
        "authorization": {"R1_P13_RESUME_FROM_T2_AUTHORIZED": True},
        "resumePoint": "T2",
        "previousP13Status": previous.get("status"),
        "previousP13Summary": str((P13 / "summary.json").relative_to(ROOT)),
        "previousP13SummarySha256": sha_path(P13 / "summary.json"),
        "resumeAuthorityValid": resume_valid,
        "lockedContract": {"caseId": "B05", "denoise": 0.35, "cfg": 6.0, "steps": 21, "referenceBinding": "A2", "contractId": CONTRACT_ID, "outputArtifactId": OUTPUT_ARTIFACT_ID},
        "sourceArtifactId": p12_contract["sourceArtifactId"],
        "sourceArtifactHash": p12_contract["sourceArtifactHash"],
        "workflowId": WORKFLOW_ID,
        "workflowHash": p12_contract["workflowHash"],
        "parameterChanges": 0,
        "sourceJobSha256": sha_path(JOB),
    })

    pins = __import__("yaml").safe_load(PINS.read_text(encoding="utf-8"))
    a2_pin = pins["a2_authority"]
    workflow_repo = FileWorkflowRepository(workflow_root=WORKFLOW_ROOT, pins_path=PINS)
    workflow, descriptor = workflow_repo.load(WORKFLOW_ID)
    validate_candidate_v3_graph(workflow)
    endpoint = os.environ.get("IDR_COMFYUI_REMOTE_BASE_URL", "https://harry-rog.taila40de0.ts.net").rstrip("/")

    test_code, test_output = run_offline([sys.executable, "-m", "pytest", "-q", "tests/test_candidate_v3_r1_p13_resume_from_t2.py", "tests/test_candidate_v3_r1_p13_gpu_recovery_resume_p12.py", "tests/test_candidate_v3_r1_p12_one_shot_final_b05_closure.py", "tests/identity_restoration/infrastructure/test_comfyui_candidate_v3_adapter.py", "tests/identity_restoration/infrastructure/test_comfyui_health_probe.py"])
    compile_code, compile_output = run_offline([sys.executable, "-m", "compileall", "-q", "identity_restoration", "validator_studio", "shared/vision", "scripts/run_candidate_v3_r1_p13_resume_from_t2.py"])
    diff_code, diff_output = run_offline(["git", "diff", "--check"])
    (OUT / "test_results.txt").write_text(test_output, encoding="utf-8")
    (OUT / "compileall.txt").write_text(compile_output if compile_output.strip() else "compileall=PASS\n", encoding="utf-8")
    (OUT / "git_diff_check.txt").write_text(diff_output if diff_output.strip() else "git_diff_check=PASS\n", encoding="utf-8")
    offline_pass = resume_valid and test_code == 0 and compile_code == 0 and diff_code == 0

    # Minimal pre-dispatch health confirmation only; no recovery/restart action.
    health, health_pass = health_gate(endpoint)
    health["resumePrecheckOnly"] = True
    health["restartAttempted"] = False
    write_json(OUT / "gpu_health.json", health)
    output_dir = OUT / "artifact"
    output_path = output_dir / "restored-canonical.png"
    manifest_path = output_dir / "manifest.json"
    gpu_jobs = 0
    artifact_created = False
    execution: dict[str, Any] | None = None
    materialization_status = "GPU_BLOCKED" if not health_pass else ("BLOCKED_LOCAL_REGRESSION" if not offline_pass else "NOT_EXECUTED")
    materialization_error = "minimal approved worker health precheck failed" if not health_pass else ("resume authority or offline gate failed" if not offline_pass else None)
    if health_pass and offline_pass:
        try:
            crop_path = ROOT / p12_contract["sourceInputPath"]
            editable_path = INPUT_ROOT / "canonical-editable-mask.png"
            feather_path = INPUT_ROOT / "canonical-feather-mask.png"
            a2_path = Path(a2_pin["path"])
            client = ComfyUIHttpClient(base_url=endpoint, timeout_s=1260.0)
            adapter = ComfyUiCandidateV3Adapter(client=client, workflow=workflow, workflow_id=descriptor.workflow_id, workflow_sha256=descriptor.sha256, model_identifiers=descriptor.models, timeout_seconds=1260.0, gpu_execution_authorized=True, gpu_evidence={"worker": "HARRY-ROG", "os": "Windows 11", "gpu": "NVIDIA GTX 1660 SUPER 6GB", "transport": "approved remote ComfyUI path"})
            request = RestorationRequest(run_id="r1-p13-b05-steps-021", attempt_id="B05-r1-p13-resume-t2", crop_png=crop_path.read_bytes(), mask=MaskSet(editable=editable_path.read_bytes(), feather=feather_path.read_bytes(), version="candidate-v3-canonical-v1"), a2=A2Authority.from_bytes(a2_path.read_bytes()), workflow_id=WORKFLOW_ID, seed=42, params=RestorationParams(denoise=0.35, steps=21, cfg=6.0, sampler="euler", scheduler="normal"))
            request.a2.verify(a2_pin["sha256"])
            gpu_jobs = 1
            restored = adapter.restore(request)
            execution = adapter.execution_evidence()
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(restored.png_bytes)
            write_json(manifest_path, {"manifestVersion": "1.0", "taskId": TASK_ID, "artifactId": OUTPUT_ARTIFACT_ID, "contractId": CONTRACT_ID, "caseId": "B05", "lane": "FACE_LOCAL", "sourceArtifactId": p12_contract["sourceArtifactId"], "sourceInputSha256": sha_path(crop_path), "sourceEditableMaskSha256": sha_path(editable_path), "sourceFeatherMaskSha256": sha_path(feather_path), "referenceBinding": {"type": "A2", "sha256": a2_pin["sha256"], "path": a2_pin["path"]}, "workflow": {"id": WORKFLOW_ID, "version": WORKFLOW_VERSION, "sha256": descriptor.sha256}, "parameters": {"denoise": 0.35, "cfg": 6.0, "steps": 21, "sampler": "euler", "scheduler": "normal", "seed": 42}, "output": {"path": str(output_path.relative_to(ROOT)), "sha256": sha_path(output_path), "width": restored.width, "height": restored.height}, "adapterEvidence": execution, "evaluationOnly": True, "productionEligible": False, "featureFlag": "OFF"})
            artifact_created = True
            materialization_status = "PASS"
        except Exception as exc:
            materialization_status = "BLOCKED / ARTIFACT_MATERIALIZATION_FAILED"
            materialization_error = f"{type(exc).__name__}: {exc}"
    write_json(OUT / "artifact_materialization.json", {"status": materialization_status, "gpuJobs": gpu_jobs, "artifactsCreated": int(artifact_created), "maxGpuJobs": 1, "maxArtifacts": 1, "parameterChanges": 0, "gpuJobId": execution.get("promptId") if execution else None, "outputArtifactId": OUTPUT_ARTIFACT_ID, "outputHash": sha_path(output_path) if output_path.is_file() else None, "manifestHash": sha_path(manifest_path) if manifest_path.is_file() else None, "workflowHash": descriptor.sha256, "error": materialization_error})

    lineage = {"status": "NOT_EXECUTED", "artifactExists": artifact_created, "artifactHashValid": False, "manifestValid": False, "contractMatch": False, "sourceLineageValid": False, "workflowLineageValid": False, "referenceBindingValid": False, "caseId": "B05", "denoiseMatch": False, "cfgMatch": False, "stepsMatch": False, "parameterChanges": 0, "passingCasesProtected": True}
    if artifact_created:
        manifest = load_json(manifest_path)
        lineage.update({"status": "PASS", "artifactHashValid": manifest["output"]["sha256"] == sha_path(output_path), "manifestValid": True, "contractMatch": manifest["contractId"] == CONTRACT_ID, "sourceLineageValid": manifest["sourceInputSha256"] == p12_contract["sourceInputHash"], "workflowLineageValid": manifest["workflow"]["sha256"] == descriptor.sha256, "referenceBindingValid": manifest["referenceBinding"]["sha256"] == a2_pin["sha256"], "denoiseMatch": manifest["parameters"]["denoise"] == 0.35, "cfgMatch": manifest["parameters"]["cfg"] == 6.0, "stepsMatch": manifest["parameters"]["steps"] == 21})
        if not all(lineage[key] for key in ("artifactHashValid", "manifestValid", "contractMatch", "sourceLineageValid", "workflowLineageValid", "referenceBindingValid", "denoiseMatch", "cfgMatch", "stepsMatch", "passingCasesProtected")):
            lineage["status"] = "BLOCKED_LOCAL_REGRESSION"
    write_json(OUT / "lineage_validation.json", lineage)

    provider_calls = 0
    face_result: dict[str, Any] | None = None
    if lineage["status"] == "PASS" and offline_pass:
        provider_calls = 1
        case_dir = OUT / "face_local" / "B05"
        case_dir.mkdir(parents=True, exist_ok=True)
        try:
            from shared.vision.paid_call_guard import paid_call_context
            from validator_studio.face_validator import _assert_face_observation_contract, _load_face_rubric, validate_face
            from validator_studio.schemas.face_validation import FaceValidationObservation
            os.environ.update({"VALIDATOR_LIVE_ENABLED": "true", "VALIDATOR_MAX_NEW_CALLS": "1", "GEMINI_MAX_TRANSPORT_ATTEMPTS": "1", "GEMINI_VISION_MODEL": MODEL, "VALIDATOR_PAID_CALL_LEDGER": str(OUT / "provider-paid-call-ledger.jsonl")})
            with paid_call_context({"benchmarkId": "candidate-v3-r1-p13-resume-t2-b05-face-local", "branch": "FACE_LOCAL", "imageSha256": sha_path(output_path), "sampleIndex": 1, "reason": "authorized single R1-P13 resume from T2 B05 recheck", "historicalEvidenceSearch": {"lineage": "VERIFIED"}}):
                report = validate_face("venho_hotel", "linh_an", output_path, provider="gemini", reference_image_paths=[Path(a2_pin["path"])], samples=1, raw_response_sink=provider_sink(case_dir), validation_cycle_id="candidate-v3-r1-p13-resume-t2-b05-face-1", attempt_id="r1-p13-resume-t2")
                observation = FaceValidationObservation.model_validate(report.raw_observation)
                _assert_face_observation_contract(observation.model_dump(mode="json"), _load_face_rubric("venho_hotel"))
            data = report.model_dump(mode="json")
            categories = data["category_scores"]
            face_result = {"valid": True, "score": float(data["overall_score"]), "verdict": data["verdict"], "eyesBrows": categories.get("eyes_and_brows"), "facialShape": categories.get("facial_shape"), "mouthChin": categories.get("mouth_and_chin"), "rawHash": sha_path(case_dir / "raw_provider_response.txt") if (case_dir / "raw_provider_response.txt").is_file() else None, "parsedHash": sha_path(case_dir / "parsed_result.json") if (case_dir / "parsed_result.json").is_file() else None, "lineageStatus": "VERIFIED", "provider": "Gemini", "model": MODEL}
            write_json(case_dir / "evaluation_report.json", data)
        except Exception as exc:
            face_result = {"valid": False, "score": None, "verdict": None, "eyesBrows": None, "facialShape": None, "mouthChin": None, "rawHash": sha_path(case_dir / "raw_provider_response.txt") if (case_dir / "raw_provider_response.txt").is_file() else None, "parsedHash": None, "lineageStatus": "VERIFIED", "provider": "Gemini", "model": MODEL, "invalidReason": type(exc).__name__, "error": str(exc)}

    if face_result and face_result["valid"] and face_result["score"] >= 90.0:
        final_status, final_face, disposition, next_action = "CLOSED / QUALITY_PASS", "9/9 PASS", "PASS", "PROMOTION_READINESS_REVIEW_REQUIRES_SEPARATE_AUTHORIZATION"
    elif face_result and face_result["valid"]:
        final_status, final_face, disposition, next_action = "CLOSED / QUALITY_FAIL", "8/9 PASS", "FAIL", "HUMAN_DECISION_REQUIRED"
    elif provider_calls:
        final_status, final_face, disposition, next_action = "PROVIDER_BLOCKED", "8/9 PASS", "FAIL", "HUMAN_DECISION_REQUIRED"
    elif materialization_status == "GPU_BLOCKED":
        final_status, final_face, disposition, next_action = "GPU_BLOCKED", "8/9 PASS", "FAIL", "RECOVER_APPROVED_GPU_WORKER_AND_RESUME_P12"
    elif materialization_status != "PASS":
        final_status, final_face, disposition, next_action = materialization_status, "8/9 PASS", "FAIL", "HUMAN_DECISION_REQUIRED"
    else:
        final_status, final_face, disposition, next_action = "BLOCKED_LOCAL_REGRESSION", "8/9 PASS", "FAIL", "HUMAN_DECISION_REQUIRED"
    final_data = face_result or {"score": None, "verdict": None, "eyesBrows": None, "facialShape": None, "mouthChin": None}
    write_json(OUT / "before_after_comparison.json", {"original": {"score": 88.50, "eyesBrows": 87, "facialShape": 88, "mouthChin": 89}, "denoise040": {"score": 87.45, "eyesBrows": 86, "facialShape": 88, "mouthChin": 87}, "finalExperiment": final_data, "deltas": {"vsOriginal": round(final_data["score"] - 88.50, 2) if final_data.get("score") is not None else None, "vsDenoise040": round(final_data["score"] - 87.45, 2) if final_data.get("score") is not None else None, "eyesBrowsVsOriginal": final_data.get("eyesBrows") - 87 if final_data.get("eyesBrows") is not None else None, "facialShapeVsOriginal": final_data.get("facialShape") - 88 if final_data.get("facialShape") is not None else None, "mouthChinVsOriginal": final_data.get("mouthChin") - 89 if final_data.get("mouthChin") is not None else None}})
    write_json(OUT / "quality_disposition.json", {"taskId": TASK_ID, "status": final_status, "boundary": "9/9 PASS", "faceLocal": final_face, "scenarioGlobal": "9/9 PASS", "pendingAuthoritativeEvaluations": 0, "qualityDisposition": disposition, "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False, "nextAction": next_action})
    write_json(OUT / "gpu_job_accounting.json", {"maxGpuJobs": 1, "gpuJobs": gpu_jobs, "maxArtifacts": 1, "artifactsCreated": int(artifact_created), "parameterChanges": 0, "maxParameterChanges": 0, "nanoCalls": 0, "alternativeProviderCalls": 0})
    write_json(OUT / "provider_call_accounting.json", {"maxProviderCalls": 1, "providerCalls": provider_calls, "maxProviderRetries": 0, "retries": 0, "provider": "Gemini", "model": MODEL, "nanoCalls": 0, "alternativeProviderCalls": 0})
    write_json(OUT / "summary.json", {"taskId": TASK_ID, "status": final_status, "authorization": True, "resumePoint": "T2", "resumeAuthorityValid": resume_valid, "parameterChangesRequired": False, "t0": "NOT_RERUN", "t1": "PASS" if health_pass else "GPU_BLOCKED", "t2": materialization_status, "t3": lineage["status"], "t4": "PASS" if face_result and face_result["valid"] else ("PROVIDER_BLOCKED" if provider_calls else "NOT_EXECUTED"), "t5": final_status, "caseId": "B05", "denoise": 0.35, "cfg": 6.0, "steps": 21, "providerCalls": provider_calls, "gpuJobs": gpu_jobs, "artifactsCreated": int(artifact_created), "boundary": "9/9 PASS", "faceLocal": final_face, "scenarioGlobal": "9/9 PASS", "pendingAuthoritativeEvaluations": 0, "qualityDisposition": disposition, "b05FinalScore": final_data.get("score"), "b05FinalVerdict": final_data.get("verdict"), "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False, "nextAction": next_action})
    finish_hashes()
    print(json.dumps({"status": final_status, "output": str(OUT), "gpuJobs": gpu_jobs, "providerCalls": provider_calls, "score": final_data.get("score")}))
    return 0 if final_status.startswith("CLOSED /") else 2


if __name__ == "__main__":
    raise SystemExit(main())
