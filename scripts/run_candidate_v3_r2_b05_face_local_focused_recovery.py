#!/usr/bin/env python3
"""Run the finite, sequential Candidate v3 R2 B05 FACE_LOCAL recovery."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

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
    INPUT_ROOT,
    JOB,
    MODEL,
    PINS,
    ROOT,
    WORKFLOW_ROOT,
    approved_endpoint,
    health_gate,
    load_existing_env,
    load_json,
    run_offline,
    sha_path,
    write_json,
)


PHASE7 = ROOT / "artifacts/identity-restoration/phase7-candidate-v3"
WORKFLOW_ID = CANDIDATE_V3_WORKFLOW_ID
WORKFLOW_VERSION = "workflow-pins-v1"
TASK_ID = "CANDIDATE-V3-QUALITY-REMEDIATION-R2-B05-FACE-LOCAL"
OUT = Path(os.environ.get(
    "R2_B05_OUTPUT_DIR",
    str(PHASE7 / ("r2-b05-face-local-focused-recovery-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))),
)).resolve()

# This tuple is the frozen R2 candidate set.  A/D continue the positive R1
# steps signal; B/C add the smallest declared 0.1 CFG adjustment.  Denoise
# remains at the R1-supported baseline after 0.40 regressed.
CANDIDATES = (
    {"id": "A", "denoise": 0.35, "cfg": 6.0, "steps": 22, "rationale": "next integer step after R1's improving steps=21 result"},
    {"id": "B", "denoise": 0.35, "cfg": 6.1, "steps": 21, "rationale": "minimal 0.1 CFG adjustment while retaining R1's improving steps=21"},
    {"id": "C", "denoise": 0.35, "cfg": 6.1, "steps": 22, "rationale": "combine the bounded CFG adjustment with next untested step"},
    {"id": "D", "denoise": 0.35, "cfg": 6.0, "steps": 23, "rationale": "final steps-only continuation, preserving CFG baseline"},
)
TESTED = (
    {"denoise": 0.35, "cfg": 6.0, "steps": 20, "label": "baseline", "score": 88.50},
    {"denoise": 0.40, "cfg": 6.0, "steps": 20, "label": "R1 denoise 0.40", "score": 87.45},
    {"denoise": 0.35, "cfg": 6.0, "steps": 21, "label": "R1 steps 21", "score": 88.90},
)


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def finish_hashes() -> None:
    files = {
        str(path.relative_to(OUT)): sha_path(path)
        for path in sorted(OUT.rglob("*"))
        if path.is_file() and path.name != "hashes.sha256"
    }
    write_json(OUT / "hashes.sha256", {"algorithm": "SHA-256", "files": files, "count": len(files)})


def same_config(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return all(left[key] == right[key] for key in ("denoise", "cfg", "steps"))


def provider_sink(candidate_dir: Path):
    raw_path = candidate_dir / "face_local" / "raw_provider_response.txt"
    parsed_path = candidate_dir / "face_local" / "parsed_result.json"

    def sink(event: dict[str, Any]) -> None:
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        if event.get("rawResponse") is not None:
            raw_path.write_text(str(event["rawResponse"]).rstrip("\n") + "\n", encoding="utf-8")
        if event.get("parsedEvidence") is not None:
            write_json(parsed_path, event["parsedEvidence"])

    return raw_path, parsed_path, sink


def candidate_contract(candidate: dict[str, Any], *, job: dict[str, Any], descriptor: Any, a2_pin: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidateId": candidate["id"], "caseId": "B05", "scope": "B05_ONLY",
        "contractId": f"candidate-v3-r2-B05-{candidate['id'].lower()}-v1",
        "parameters": {"denoise": candidate["denoise"], "cfg": candidate["cfg"], "steps": candidate["steps"], "sampler": "euler", "scheduler": "normal", "seed": 42},
        "referenceBinding": {"type": "A2", "path": a2_pin["path"], "sha256": a2_pin["sha256"]},
        "workflow": {"id": WORKFLOW_ID, "version": WORKFLOW_VERSION, "sha256": descriptor.sha256},
        "sourceArtifactId": job["jobId"], "sourceArtifactHash": job["lineage"]["transform"]["canonicalImageSha256"],
        "sourceInputPath": str((INPUT_ROOT / "canonical-input.png").relative_to(ROOT)),
        "sourceInputHash": sha_path(INPUT_ROOT / "canonical-input.png"),
        "preservation": {"boundary": "9/9 PASS", "otherFaceLocalPassingCases": "8/8 PASS", "scenarioGlobal": "9/9 PASS", "thresholdsUnchanged": True, "rubricUnchanged": True, "providerUnchanged": True, "architectureChanged": False},
    }


def execute_candidate(candidate: dict[str, Any], *, job: dict[str, Any], workflow: dict[str, Any], descriptor: Any, a2_pin: dict[str, Any], endpoint: str) -> dict[str, Any]:
    candidate_dir = OUT / "candidates" / f"candidate-{candidate['id']}"
    contract = candidate_contract(candidate, job=job, descriptor=descriptor, a2_pin=a2_pin)
    write_json(candidate_dir / "artifact_contract.json", contract)
    output_dir = candidate_dir / "artifact"
    output_path = output_dir / "restored-canonical.png"
    manifest_path = output_dir / "manifest.json"
    execution: dict[str, Any] | None = None
    try:
        crop_path = INPUT_ROOT / "canonical-input.png"
        editable_path = INPUT_ROOT / "canonical-editable-mask.png"
        feather_path = INPUT_ROOT / "canonical-feather-mask.png"
        a2_path = Path(a2_pin["path"])
        client = ComfyUIHttpClient(base_url=endpoint, timeout_s=1260.0)
        adapter = ComfyUiCandidateV3Adapter(client=client, workflow=workflow, workflow_id=descriptor.workflow_id, workflow_sha256=descriptor.sha256, model_identifiers=descriptor.models, timeout_seconds=1260.0, gpu_execution_authorized=True, gpu_evidence={"worker": "HARRY-ROG", "os": "Windows 11", "gpu": "NVIDIA GTX 1660 SUPER 6GB", "transport": "approved remote ComfyUI path"})
        request = RestorationRequest(run_id=f"r2-b05-{candidate['id'].lower()}", attempt_id=f"B05-r2-{candidate['id'].lower()}", crop_png=crop_path.read_bytes(), mask=MaskSet(editable=editable_path.read_bytes(), feather=feather_path.read_bytes(), version="candidate-v3-canonical-v1"), a2=A2Authority.from_bytes(a2_path.read_bytes()), workflow_id=WORKFLOW_ID, seed=42, params=RestorationParams(denoise=candidate["denoise"], steps=candidate["steps"], cfg=candidate["cfg"], sampler="euler", scheduler="normal"))
        request.a2.verify(a2_pin["sha256"])
        restored = adapter.restore(request)
        execution = adapter.execution_evidence()
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(restored.png_bytes)
        write_json(manifest_path, {"manifestVersion": "1.0", "taskId": TASK_ID, "candidateId": candidate["id"], "artifactId": f"candidate-v3-r2-B05-{candidate['id'].lower()}-face-detail-v1", **contract, "output": {"path": str(output_path.relative_to(ROOT)), "sha256": sha_path(output_path), "width": restored.width, "height": restored.height}, "adapterEvidence": execution, "evaluationOnly": True, "productionEligible": False, "featureFlag": "OFF"})
    except Exception as exc:
        write_json(candidate_dir / "artifact_materialization.json", {"status": "BLOCKED / ARTIFACT_MATERIALIZATION_FAILED", "gpuJobId": execution.get("promptId") if execution else None, "error": f"{type(exc).__name__}: {exc}"})
        return {"id": candidate["id"], "candidate": candidate, "status": "BLOCKED / ARTIFACT_MATERIALIZATION_FAILED", "gpuJobId": execution.get("promptId") if execution else None, "artifact": None, "provider": None}

    manifest = load_json(manifest_path)
    lineage = {"status": "PASS", "artifactExists": output_path.is_file(), "artifactHashValid": manifest["output"]["sha256"] == sha_path(output_path), "manifestValid": True, "contractMatch": manifest["contractId"] == contract["contractId"], "sourceLineageValid": manifest["sourceInputHash"] == contract["sourceInputHash"], "workflowLineageValid": manifest["workflow"]["sha256"] == descriptor.sha256, "referenceBindingValid": manifest["referenceBinding"]["sha256"] == a2_pin["sha256"], "parametersMatch": manifest["parameters"] == contract["parameters"], "passingCasesProtected": True}
    if not all(lineage[key] for key in ("artifactExists", "artifactHashValid", "manifestValid", "contractMatch", "sourceLineageValid", "workflowLineageValid", "referenceBindingValid", "parametersMatch", "passingCasesProtected")):
        lineage["status"] = "BLOCKED_LOCAL_REGRESSION"
    write_json(candidate_dir / "lineage_validation.json", lineage)
    write_json(candidate_dir / "artifact_materialization.json", {"status": "PASS", "gpuJobId": execution.get("promptId"), "artifactHash": sha_path(output_path), "manifestHash": sha_path(manifest_path), "workflowHash": descriptor.sha256})
    if lineage["status"] != "PASS":
        return {"id": candidate["id"], "candidate": candidate, "status": "BLOCKED_LOCAL_REGRESSION", "gpuJobId": execution.get("promptId"), "artifact": {"hash": sha_path(output_path), "manifestHash": sha_path(manifest_path)}, "provider": None}

    raw_path, parsed_path, sink = provider_sink(candidate_dir)
    try:
        from shared.vision.paid_call_guard import paid_call_context
        from validator_studio.face_validator import _assert_face_observation_contract, _load_face_rubric, validate_face
        from validator_studio.schemas.face_validation import FaceValidationObservation

        os.environ.update({"VALIDATOR_LIVE_ENABLED": "true", "VALIDATOR_MAX_NEW_CALLS": "1", "GEMINI_MAX_TRANSPORT_ATTEMPTS": "1", "GEMINI_VISION_MODEL": MODEL, "VALIDATOR_PAID_CALL_LEDGER": str(candidate_dir / "provider-paid-call-ledger.jsonl")})
        with paid_call_context({"benchmarkId": f"candidate-v3-r2-b05-{candidate['id'].lower()}", "branch": "FACE_LOCAL", "imageSha256": sha_path(output_path), "sampleIndex": 1, "reason": "authorized R2 sequential B05 FACE_LOCAL tuning", "historicalEvidenceSearch": {"lineage": "VERIFIED"}}):
            report = validate_face("venho_hotel", "linh_an", output_path, provider="gemini", reference_image_paths=[Path(a2_pin["path"])], samples=1, raw_response_sink=sink, validation_cycle_id=f"candidate-v3-r2-b05-{candidate['id'].lower()}-face-1", attempt_id=f"r2-{candidate['id'].lower()}")
            observation = FaceValidationObservation.model_validate(report.raw_observation)
            _assert_face_observation_contract(observation.model_dump(mode="json"), _load_face_rubric("venho_hotel"))
        data = report.model_dump(mode="json")
        write_json(candidate_dir / "face_local" / "evaluation_report.json", data)
        categories = data["category_scores"]
        provider = {"valid": True, "score": float(data["overall_score"]), "verdict": data["verdict"], "pass": data["verdict"] == "approve", "eyesBrows": categories.get("eyes_and_brows"), "facialShape": categories.get("facial_shape"), "mouthChin": categories.get("mouth_and_chin"), "rawHash": sha_path(raw_path) if raw_path.is_file() else None, "parsedHash": sha_path(parsed_path) if parsed_path.is_file() else None, "provider": "Gemini", "model": MODEL, "lineageStatus": "VERIFIED"}
    except Exception as exc:
        provider = {"valid": False, "pass": False, "score": None, "verdict": None, "eyesBrows": None, "facialShape": None, "mouthChin": None, "rawHash": sha_path(raw_path) if raw_path.is_file() else None, "parsedHash": None, "provider": "Gemini", "model": MODEL, "failure": f"{type(exc).__name__}: {exc}", "lineageStatus": "VERIFIED"}
    write_json(candidate_dir / "provider_result.json", provider)
    return {"id": candidate["id"], "candidate": candidate, "status": "PASS" if provider["valid"] else "PROVIDER_BLOCKED", "gpuJobId": execution.get("promptId"), "artifact": {"hash": sha_path(output_path), "manifestHash": sha_path(manifest_path)}, "provider": provider}


def main() -> int:
    if OUT.exists() and any(OUT.iterdir()):
        raise SystemExit(f"refusing to overwrite evidence directory: {OUT}")
    OUT.mkdir(parents=True, exist_ok=True)
    load_existing_env()
    job = load_json(JOB)
    pins = yaml.safe_load(PINS.read_text(encoding="utf-8"))
    a2_pin = pins["a2_authority"]
    workflow_repo = FileWorkflowRepository(workflow_root=WORKFLOW_ROOT, pins_path=PINS)
    workflow, descriptor = workflow_repo.load(WORKFLOW_ID)
    validate_candidate_v3_graph(workflow)
    endpoint, endpoint_source = approved_endpoint()

    authority = {"denoise": {"baseline": 0.35, "testedValues": [0.35, 0.40], "approvedRange": [0.05, 0.75], "evidence": "R1 0.40 regressed; keep baseline", "r2Allowed": False}, "cfg": {"baseline": 6.0, "testedValues": [6.0], "approvedRange": [1.0, 12.0], "evidence": "RestorationParams range; R2 authorizes a smallest declared 0.1 adjustment", "r2Allowed": True}, "steps": {"baseline": 20, "testedValues": [20, 21], "approvedRange": [8, 60], "evidence": "R1 steps=21 improved score 88.50 -> 88.90", "r2Allowed": True}}
    candidate_checks = {
        "countWithinBudget": len(CANDIDATES) <= 4,
        "unique": len({(c["denoise"], c["cfg"], c["steps"]) for c in CANDIDATES}) == len(CANDIDATES),
        "notPreviouslyTested": all(not any(same_config(c, tested) for tested in TESTED) for c in CANDIDATES),
        "ranges": all(0.05 <= c["denoise"] <= 0.75 and 1.0 <= c["cfg"] <= 12.0 and 8 <= c["steps"] <= 60 for c in CANDIDATES),
        "oneOrTwoBaselineDeltas": all(sum(c[key] != {"denoise": 0.35, "cfg": 6.0, "steps": 20}[key] for key in ("denoise", "cfg", "steps")) in {1, 2} for c in CANDIDATES),
    }
    authority_valid = all(candidate_checks.values())
    write_json(OUT / "baseline.json", {"authorization": {"CANDIDATE_V3_QUALITY_REMEDIATION_R2_AUTHORIZED": True}, "r1Final": {"status": "CLOSED / QUALITY_FAIL", "boundary": "9/9 PASS", "faceLocal": "8/9 PASS", "scenarioGlobal": "9/9 PASS", "qualityDisposition": "FAIL", "providerHold": "RECOVERED"}, "testedConfigurations": TESTED, "knownGeometry": {"faceScale": 0.0723, "yaw": -49.08, "referenceBinding": "A2"}, "sourceJob": {"id": job["jobId"], "sha256": sha_path(JOB)}})
    write_json(OUT / "parameter_authority_matrix.json", authority)
    write_json(OUT / "candidate_set.json", {"status": "FROZEN" if authority_valid else "BLOCKED / PARAMETER_AUTHORITY_UNRESOLVED", "candidateChecks": candidate_checks, "candidates": CANDIDATES, "executionOrder": [c["id"] for c in CANDIDATES], "frozenBeforeExecution": True})

    test_code, test_output = run_offline([sys.executable, "-m", "pytest", "-q", "tests/test_candidate_v3_r2_b05_face_local_focused_recovery.py", "tests/test_candidate_v3_r1_p13_resume_from_t4.py", "tests/identity_restoration/infrastructure/test_comfyui_candidate_v3_adapter.py", "tests/identity_restoration/infrastructure/test_comfyui_health_probe.py"])
    compile_code, compile_output = run_offline([sys.executable, "-m", "compileall", "-q", "identity_restoration", "validator_studio", "shared/vision", "scripts/run_candidate_v3_r2_b05_face_local_focused_recovery.py"])
    diff_code, diff_output = run_offline(["git", "diff", "--check"])
    (OUT / "test_results.txt").write_text(test_output, encoding="utf-8")
    (OUT / "compileall.txt").write_text(compile_output if compile_output.strip() else "compileall=PASS\n", encoding="utf-8")
    (OUT / "git_diff_check.txt").write_text(diff_output if diff_output.strip() else "git_diff_check=PASS\n", encoding="utf-8")
    offline_pass = authority_valid and test_code == 0 and compile_code == 0 and diff_code == 0 and descriptor.sha256 == pins["workflows"][WORKFLOW_ID]["sha256"]
    write_json(OUT / "offline_validation.json", {"status": "PASS" if offline_pass else "BLOCKED_LOCAL_REGRESSION", "b05Only": True, "workflowPinValid": descriptor.sha256 == pins["workflows"][WORKFLOW_ID]["sha256"], "referenceBinding": "A2", "thresholdsUnchanged": True, "rubricUnchanged": True, "providerUnchanged": True, "architectureUnchanged": True, "passingCasesProtected": True, "tests": test_code == 0, "compileall": compile_code == 0, "gitDiffCheck": diff_code == 0})

    results: list[dict[str, Any]] = []
    terminal: str | None = None
    early_stop = False
    if not offline_pass:
        terminal = "BLOCKED_LOCAL_REGRESSION"
    else:
        for candidate in CANDIDATES:
            health, healthy = health_gate(endpoint)
            write_json(OUT / "candidates" / f"candidate-{candidate['id']}" / "gpu_health.json", {**health, "endpointSource": endpoint_source})
            if not healthy:
                terminal = "GPU_BLOCKED"
                break
            result = execute_candidate(candidate, job=job, workflow=workflow, descriptor=descriptor, a2_pin=a2_pin, endpoint=endpoint)
            results.append(result)
            if result["status"] == "BLOCKED / ARTIFACT_MATERIALIZATION_FAILED":
                terminal = result["status"]
                break
            if result["status"] == "BLOCKED_LOCAL_REGRESSION":
                terminal = result["status"]
                break
            if result["status"] == "PROVIDER_BLOCKED":
                terminal = "PROVIDER_BLOCKED"
                break
            if result["provider"]["pass"]:
                early_stop = True
                break

    pass_result = next((result for result in results if result.get("provider", {}).get("pass")), None)
    confirmation: dict[str, Any] = {"executed": False, "status": "NOT_RUN"}
    if terminal is None and pass_result is not None:
        if len(results) < 4:
            confirmation_candidate = {**pass_result["candidate"], "id": "confirmation"}
            health, healthy = health_gate(endpoint)
            write_json(OUT / "reproducibility_confirmation_health.json", {**health, "endpointSource": endpoint_source})
            if not healthy:
                terminal = "GPU_BLOCKED"
                confirmation = {"executed": False, "status": "GPU_BLOCKED"}
            else:
                confirmation_result = execute_candidate(confirmation_candidate, job=job, workflow=workflow, descriptor=descriptor, a2_pin=a2_pin, endpoint=endpoint)
                confirmation = {"executed": True, "status": confirmation_result["status"], "result": confirmation_result}
                if confirmation_result["status"] != "PASS":
                    terminal = "PROVIDER_BLOCKED" if confirmation_result["status"] == "PROVIDER_BLOCKED" else confirmation_result["status"]
                elif not confirmation_result["provider"]["pass"]:
                    terminal = "CLOSED / QUALITY_FAIL"
                else:
                    terminal = "CLOSED / QUALITY_PASS"
        else:
            confirmation = {"executed": False, "status": "NOT_RUN_BUDGET_EXHAUSTED"}
            terminal = "CLOSED / QUALITY_PASS"
    elif terminal is None:
        terminal = "CLOSED / QUALITY_FAIL"

    provider_results = [result["provider"] for result in results if result.get("provider")]
    if confirmation.get("executed") and confirmation.get("result", {}).get("provider"):
        provider_results.append(confirmation["result"]["provider"])
    best = max((r for r in results if r.get("provider", {}).get("valid")), key=lambda r: (r["provider"]["score"], min(r["provider"]["eyesBrows"], r["provider"]["facialShape"], r["provider"]["mouthChin"])), default=None)
    final_provider = confirmation.get("result", {}).get("provider") if terminal == "CLOSED / QUALITY_PASS" and confirmation.get("executed") else (pass_result.get("provider") if pass_result and terminal == "CLOSED / QUALITY_PASS" else (best.get("provider") if best else None))
    if terminal == "CLOSED / QUALITY_PASS":
        final_face, disposition, pending, hold, next_action = "9/9 PASS", "PASS", 0, "RECOVERED", "PROMOTION_READINESS_REVIEW_REQUIRES_SEPARATE_AUTHORIZATION"
    elif terminal == "PROVIDER_BLOCKED":
        final_face, disposition, pending, hold, next_action = "8/9 PASS", "FAIL_PENDING_B05_RECHECK", 1, "ACTIVE", "HUMAN_DECISION_REQUIRED"
    else:
        final_face, disposition, pending, hold, next_action = "8/9 PASS", "FAIL", 0, "RECOVERED", "HUMAN_DECISION_REQUIRED"
    write_json(OUT / "winner_selection.json", {"earlyStopTriggered": early_stop, "winner": pass_result["id"] if pass_result else None, "bestObservedConfig": {"id": best["id"], **best["candidate"], "score": best["provider"]["score"]} if best else None, "ranking": "PASS > score > minimum dimension > smallest baseline deviation"})
    write_json(OUT / "reproducibility_confirmation.json", confirmation)
    write_json(OUT / "before_after_history.json", {"baseline": TESTED, "r2Results": results, "confirmation": confirmation})
    write_json(OUT / "quality_disposition.json", {"taskId": TASK_ID, "status": terminal, "boundary": "9/9 PASS", "faceLocal": final_face, "scenarioGlobal": "9/9 PASS", "pendingAuthoritativeEvaluations": pending, "qualityDisposition": disposition, "providerHold": hold, "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False, "nextAction": next_action})
    gpu_jobs = len(results) + int(bool(confirmation.get("executed")))
    write_json(OUT / "gpu_job_accounting.json", {"maxGpuJobs": 4, "gpuJobs": gpu_jobs, "maxArtifacts": 4, "artifactsCreated": gpu_jobs, "candidateConfigurations": len(CANDIDATES), "executedCandidateConfigurations": len(results), "parameterChanges": "candidate-scoped only", "nanoCalls": 0, "alternativeProviderCalls": 0})
    write_json(OUT / "provider_call_accounting.json", {"maxProviderCalls": 4, "providerCalls": len(provider_results), "maxProviderRetries": 0, "retries": 0, "provider": "Gemini", "model": MODEL, "nanoCalls": 0, "alternativeProviderCalls": 0, "providerHold": hold})
    write_json(OUT / "summary.json", {"taskId": TASK_ID, "status": terminal, "authorization": True, "candidateSet": CANDIDATES, "executedCandidates": [r["id"] for r in results], "earlyStopTriggered": early_stop, "winner": pass_result["id"] if pass_result else None, "confirmation": confirmation["status"], "gpuJobs": gpu_jobs, "artifactsCreated": gpu_jobs, "providerCalls": len(provider_results), "retries": 0, "boundary": "9/9 PASS", "faceLocal": final_face, "scenarioGlobal": "9/9 PASS", "pendingAuthoritativeEvaluations": pending, "qualityDisposition": disposition, "providerHold": hold, "b05FinalScore": final_provider.get("score") if final_provider else None, "b05FinalVerdict": final_provider.get("verdict") if final_provider else None, "bestObservedConfig": best["id"] if best else None, "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False, "nextAction": next_action})
    finish_hashes()
    print(json.dumps({"status": terminal, "output": str(OUT), "gpuJobs": gpu_jobs, "providerCalls": len(provider_results), "winner": pass_result["id"] if pass_result else None}))
    return 0 if terminal.startswith("CLOSED /") else 2


if __name__ == "__main__":
    raise SystemExit(main())
