#!/usr/bin/env python3
"""Resume R1-P13 at T4 using the immutable artifact from the T2 run."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.run_candidate_v3_r1_p13_gpu_recovery_resume_p12 import (
    MODEL,
    ROOT,
    load_existing_env,
    load_json,
    run_offline,
    sha_path,
    write_json,
)


PHASE7 = ROOT / "artifacts/identity-restoration/phase7-candidate-v3"
PREVIOUS = PHASE7 / "r1-p13-resume-from-t2-20260902T072500Z"
ARTIFACT = PREVIOUS / "artifact/restored-canonical.png"
MANIFEST = PREVIOUS / "artifact/manifest.json"
LINEAGE = PREVIOUS / "lineage_validation.json"
TASK_ID = "R1-P13-RESUME-FROM-T4"
EXPECTED_ARTIFACT_SHA = "ce58f0ac97a74bc07eccfba9d8c96584ff38eafd5a0a53e14fb84d363a873e40"
OUT = Path(os.environ.get(
    "R1_P13_T4_OUTPUT_DIR",
    str(PHASE7 / ("r1-p13-resume-from-t4-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))),
)).resolve()


def finish_hashes() -> None:
    files = {
        str(path.relative_to(OUT)): sha_path(path)
        for path in sorted(OUT.rglob("*"))
        if path.is_file() and path.name != "hashes.sha256"
    }
    write_json(OUT / "hashes.sha256", {"algorithm": "SHA-256", "files": files, "count": len(files)})


def face_sink() -> tuple[Path, Any]:
    raw_path = OUT / "b05_raw.txt"
    parsed_path = OUT / "b05_parsed.json"

    def sink(event: dict[str, Any]) -> None:
        if event.get("rawResponse") is not None:
            raw_path.write_text(str(event["rawResponse"]).rstrip("\n") + "\n", encoding="utf-8")
        if event.get("parsedEvidence") is not None:
            write_json(parsed_path, event["parsedEvidence"])

    return raw_path, sink


def main() -> int:
    if OUT.exists() and any(OUT.iterdir()):
        raise SystemExit(f"refusing to overwrite evidence directory: {OUT}")
    OUT.mkdir(parents=True, exist_ok=True)
    load_existing_env()

    # T4-0: use the existing repository loader; only redacted presence is recorded.
    credential_present = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    adapter_ready = False
    adapter_error: str | None = None
    try:
        from shared.vision.providers.gemini_vision import GeminiVisionProvider

        if credential_present:
            GeminiVisionProvider(model=MODEL)
            adapter_ready = True
    except Exception as exc:
        adapter_error = f"{type(exc).__name__}: {exc}"
    credential_ready = credential_present and adapter_ready
    write_json(OUT / "credential_readiness.json", {
        "status": "PASS" if credential_ready else "PROVIDER_BLOCKED",
        "credentialPresent": credential_present,
        "credentialSource": "existing approved dotenv loader (source redacted)",
        "secretExposed": False,
        "provider": "Gemini",
        "model": MODEL,
        "providerAdapterReady": adapter_ready,
        "adapterError": adapter_error,
    })

    previous = load_json(PREVIOUS / "summary.json")
    manifest = load_json(MANIFEST) if MANIFEST.is_file() else {}
    lineage = load_json(LINEAGE) if LINEAGE.is_file() else {}
    artifact_hash = sha_path(ARTIFACT) if ARTIFACT.is_file() else None
    integrity = {
        "status": "PASS",
        "previousStatus": previous.get("status"),
        "previousProviderHold": previous.get("providerHold"),
        "artifactPath": str(ARTIFACT.relative_to(ROOT)),
        "artifactExists": ARTIFACT.is_file(),
        "artifactHash": artifact_hash,
        "artifactHashValid": artifact_hash == EXPECTED_ARTIFACT_SHA,
        "manifestValid": bool(manifest),
        "manifestHash": sha_path(MANIFEST) if MANIFEST.is_file() else None,
        "contractMatch": manifest.get("contractId") == "candidate-v3-r1-p12-B05-steps-021-v1",
        "parametersMatch": manifest.get("parameters") == {"denoise": 0.35, "cfg": 6.0, "steps": 21, "sampler": "euler", "scheduler": "normal", "seed": 42},
        "lineageStatus": lineage.get("status"),
        "lineageValid": lineage.get("status") == "PASS",
        "gpuJobs": 0,
        "artifactsCreated": 0,
        "parameterChanges": 0,
    }
    integrity["status"] = "PASS" if all(integrity[key] for key in ("artifactExists", "artifactHashValid", "manifestValid", "contractMatch", "parametersMatch", "lineageValid")) else "BLOCKED_LOCAL_REGRESSION"
    write_json(OUT / "artifact_integrity.json", integrity)
    write_json(OUT / "resume_baseline.json", {
        "authorization": {"R1_P13_RESUME_FROM_T4_AUTHORIZED": True},
        "resumePoint": "T4",
        "previousEvidence": str(PREVIOUS.relative_to(ROOT)),
        "previousStatus": previous.get("status"),
        "previousBlocker": previous.get("providerFailure"),
        "lockedContract": {"caseId": "B05", "denoise": 0.35, "cfg": 6.0, "steps": 21, "referenceBinding": "A2"},
        "artifactSha256": EXPECTED_ARTIFACT_SHA,
        "boundary": "9/9 PASS", "faceLocal": "8/9 PASS", "scenarioGlobal": "9/9 PASS",
        "pendingAuthoritativeEvaluations": 1, "qualityDisposition": "FAIL",
        "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False,
    })

    test_code, test_output = run_offline([sys.executable, "-m", "pytest", "-q", "tests/test_candidate_v3_r1_p13_resume_from_t4.py", "tests/test_candidate_v3_r1_p13_resume_from_t2.py", "tests/test_candidate_v3_r1_p13_gpu_recovery_resume_p12.py", "tests/identity_restoration/infrastructure/test_comfyui_candidate_v3_adapter.py"])
    compile_code, compile_output = run_offline([sys.executable, "-m", "compileall", "-q", "validator_studio", "shared/vision", "scripts/run_candidate_v3_r1_p13_resume_from_t4.py"])
    diff_code, diff_output = run_offline(["git", "diff", "--check"])
    (OUT / "test_results.txt").write_text(test_output, encoding="utf-8")
    (OUT / "compileall.txt").write_text(compile_output if compile_output.strip() else "compileall=PASS\n", encoding="utf-8")
    (OUT / "git_diff_check.txt").write_text(diff_output if diff_output.strip() else "git_diff_check=PASS\n", encoding="utf-8")
    preflight_pass = credential_ready and integrity["status"] == "PASS" and test_code == 0 and compile_code == 0 and diff_code == 0
    write_json(OUT / "offline_preflight.json", {
        "status": "PASS" if preflight_pass else ("PROVIDER_BLOCKED" if not credential_ready else "BLOCKED_LOCAL_REGRESSION"),
        "provider": "Gemini", "model": MODEL, "adapterImports": adapter_ready,
        "credentialAvailable": credential_ready, "faceLocalSchemaValid": True,
        "artifactHashValid": integrity["artifactHashValid"], "lineageValid": integrity["lineageValid"],
        "tests": test_code == 0, "compileall": compile_code == 0, "gitDiffCheck": diff_code == 0,
        "providerReadinessProbe": "NOT_PERFORMED_NO_PROVIDER_CALL_CONSUMED",
    })

    provider_calls = 0
    face_result: dict[str, Any] | None = None
    raw_path, sink = face_sink()
    if preflight_pass:
        provider_calls = 1
        try:
            from shared.vision.paid_call_guard import paid_call_context
            from validator_studio.face_validator import _assert_face_observation_contract, _load_face_rubric, validate_face
            from validator_studio.schemas.face_validation import FaceValidationObservation

            a2_path = Path(manifest["referenceBinding"]["path"])
            os.environ.update({"VALIDATOR_LIVE_ENABLED": "true", "VALIDATOR_MAX_NEW_CALLS": "1", "GEMINI_MAX_TRANSPORT_ATTEMPTS": "1", "GEMINI_VISION_MODEL": MODEL, "VALIDATOR_PAID_CALL_LEDGER": str(OUT / "provider-paid-call-ledger.jsonl")})
            with paid_call_context({"benchmarkId": "candidate-v3-r1-p13-resume-t4-b05-face-local", "branch": "FACE_LOCAL", "imageSha256": EXPECTED_ARTIFACT_SHA, "sampleIndex": 1, "reason": "authorized single R1-P13 T4 B05 recheck", "historicalEvidenceSearch": {"lineage": "VERIFIED"}}):
                report = validate_face("venho_hotel", "linh_an", ARTIFACT, provider="gemini", reference_image_paths=[a2_path], samples=1, raw_response_sink=sink, validation_cycle_id="candidate-v3-r1-p13-resume-t4-b05-face-1", attempt_id="r1-p13-resume-t4")
                observation = FaceValidationObservation.model_validate(report.raw_observation)
                _assert_face_observation_contract(observation.model_dump(mode="json"), _load_face_rubric("venho_hotel"))
            data = report.model_dump(mode="json")
            categories = data["category_scores"]
            parsed_path = OUT / "b05_parsed.json"
            write_json(parsed_path, data)
            face_result = {"valid": True, "score": float(data["overall_score"]), "verdict": data["verdict"], "eyesBrows": categories.get("eyes_and_brows"), "facialShape": categories.get("facial_shape"), "mouthChin": categories.get("mouth_and_chin"), "rawHash": sha_path(raw_path) if raw_path.is_file() else None, "parsedHash": sha_path(parsed_path), "lineageStatus": "VERIFIED", "provider": "Gemini", "model": MODEL}
        except Exception as exc:
            face_result = {"valid": False, "score": None, "verdict": None, "eyesBrows": None, "facialShape": None, "mouthChin": None, "rawHash": sha_path(raw_path) if raw_path.is_file() else None, "parsedHash": None, "lineageStatus": "VERIFIED", "provider": "Gemini", "model": MODEL, "failure": f"{type(exc).__name__}: {exc}"}

    if face_result and face_result["valid"] and face_result["score"] >= 90.0:
        final_status, final_face, disposition, pending, hold, next_action = "CLOSED / QUALITY_PASS", "9/9 PASS", "PASS", 0, "RECOVERED", "PROMOTION_READINESS_REVIEW_REQUIRES_SEPARATE_AUTHORIZATION"
    elif face_result and face_result["valid"]:
        final_status, final_face, disposition, pending, hold, next_action = "CLOSED / QUALITY_FAIL", "8/9 PASS", "FAIL", 0, "RECOVERED", "HUMAN_DECISION_REQUIRED"
    elif not credential_ready or provider_calls:
        final_status, final_face, disposition, pending, hold, next_action = "PROVIDER_BLOCKED", "8/9 PASS", "FAIL_PENDING_B05_RECHECK", 1, "ACTIVE", "HUMAN_DECISION_REQUIRED"
    else:
        final_status, final_face, disposition, pending, hold, next_action = "BLOCKED_LOCAL_REGRESSION", "8/9 PASS", "FAIL", 1, "ACTIVE", "HUMAN_DECISION_REQUIRED"
    final_data = face_result or {"score": None, "verdict": None, "eyesBrows": None, "facialShape": None, "mouthChin": None}
    write_json(OUT / "before_after_comparison.json", {"original": {"score": 88.50, "eyesBrows": 87, "facialShape": 88, "mouthChin": 89}, "denoise040": {"score": 87.45, "eyesBrows": 86, "facialShape": 88, "mouthChin": 87}, "finalExperiment": final_data, "deltas": {"vsOriginal": round(final_data["score"] - 88.50, 2) if final_data.get("score") is not None else None, "vsDenoise040": round(final_data["score"] - 87.45, 2) if final_data.get("score") is not None else None, "eyesBrowsVsOriginal": final_data.get("eyesBrows") - 87 if final_data.get("eyesBrows") is not None else None, "facialShapeVsOriginal": final_data.get("facialShape") - 88 if final_data.get("facialShape") is not None else None, "mouthChinVsOriginal": final_data.get("mouthChin") - 89 if final_data.get("mouthChin") is not None else None}})
    write_json(OUT / "quality_disposition.json", {"taskId": TASK_ID, "status": final_status, "boundary": "9/9 PASS", "faceLocal": final_face, "scenarioGlobal": "9/9 PASS", "pendingAuthoritativeEvaluations": pending, "qualityDisposition": disposition, "providerHold": hold, "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False, "nextAction": next_action})
    write_json(OUT / "provider_call_accounting.json", {"maxProviderCalls": 1, "providerCalls": provider_calls, "maxProviderRetries": 0, "retries": 0, "provider": "Gemini", "model": MODEL, "gpuJobs": 0, "artifactsCreated": 0, "parameterChanges": 0, "nanoCalls": 0, "alternativeProviderCalls": 0, "providerHold": hold, "failure": face_result.get("failure") if face_result and not face_result["valid"] else None})
    write_json(OUT / "summary.json", {"taskId": TASK_ID, "status": final_status, "authorization": True, "resumePoint": "T4", "credentialReady": credential_ready, "t4_0": "PASS" if credential_ready else "PROVIDER_BLOCKED", "t4_1": "PASS" if preflight_pass else ("PROVIDER_BLOCKED" if not credential_ready else "BLOCKED_LOCAL_REGRESSION"), "t4_2": "PASS" if face_result and face_result["valid"] else ("PROVIDER_BLOCKED" if provider_calls or not credential_ready else "NOT_EXECUTED"), "caseId": "B05", "denoise": 0.35, "cfg": 6.0, "steps": 21, "artifactHash": EXPECTED_ARTIFACT_SHA, "gpuJobs": 0, "artifactsCreated": 0, "providerCalls": provider_calls, "retries": 0, "boundary": "9/9 PASS", "faceLocal": final_face, "scenarioGlobal": "9/9 PASS", "pendingAuthoritativeEvaluations": pending, "qualityDisposition": disposition, "providerHold": hold, "b05FinalScore": final_data.get("score"), "b05FinalVerdict": final_data.get("verdict"), "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False, "nextAction": next_action})
    finish_hashes()
    print(json.dumps({"status": final_status, "output": str(OUT), "providerCalls": provider_calls, "score": final_data.get("score")}))
    return 0 if final_status.startswith("CLOSED /") else 2


if __name__ == "__main__":
    raise SystemExit(main())
