#!/usr/bin/env python3
"""Resume-safe provider execution for Candidate v3 R1-P4-R1.

This is an execution/remediation harness only.  It calls the existing
Validator Studio entrypoints against immutable Candidate v3 artifacts and
never invokes image generation, ComfyUI, or a second provider.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
P4 = ROOT / "artifacts/identity-restoration/phase7-candidate-v3/r1-p4-authoritative-validation-20260901-final"
P1 = ROOT / "artifacts/identity-restoration/phase7-candidate-v3/r1-p1-boundary-remediation-20260828"
PHASE7 = ROOT / "artifacts/identity-restoration/phase7-candidate-v3"
OUT = Path(os.environ.get(
    "R1_P4_R1_OUTPUT_DIR",
    str(ROOT / "artifacts/identity-restoration/phase7-candidate-v3" / (
        "r1-p4-r1-provider-remediation-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    )),
))
PACK_SHA = "fc185a9e47a33092fbafe357a140b65f9449bac0de28d7e20b9f33d8ddcbb406"
A2_PATH = ROOT / "assets/linh_an/A2_Front.png"
A2_SHA = "1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d"
CASES = tuple(f"B{i:02d}" for i in range(1, 10))
VALIDATOR_VERSION = "validator-studio-existing-production-entrypoint"
RETRY_POLICY = {
    "maxTransportAttemptsPerLogicalSample": 2,
    "backoffSeconds": [0.25],
    "jitter": False,
    "retryable": ["PROVIDER_503", "PROVIDER_429", "PROVIDER_TIMEOUT"],
    "nonRetryable": [
        "LOCAL_SCHEMA_BUILD_FAIL", "LOCAL_REQUEST_SERIALIZATION_FAIL",
        "PROVIDER_TRUNCATED_RESPONSE", "PROVIDER_RESPONSE_SCHEMA_FAIL",
        "AUTH_FAILURE", "UNSUPPORTED_MODEL", "MALFORMED_LOCAL_INPUT",
    ],
}


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_path(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def canonical_hash(value: Any) -> str:
    return sha_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def load_env() -> None:
    social = ROOT.parent.parent / "venho-social-content-agent"
    for path in (social / ".env.local", social / ".env", ROOT / ".env.local", ROOT / ".env"):
        if path.is_file():
            load_dotenv(path, override=False)


def job_payload(case_id: str) -> tuple[dict[str, Any], Path, Path, Path]:
    number = int(case_id[1:])
    run = "phase7-benchmark-20260828" if number <= 4 or number >= 7 else "phase7-diagnostic-20260828"
    job = json.loads((PHASE7 / "jobs" / f"{run}-{case_id}.json").read_text(encoding="utf-8"))
    return (
        job,
        P1 / case_id / "inverse-composite-remediated.png",
        PHASE7 / run / f"{case_id}-attempt-1" / "restored-canonical.png",
        PHASE7 / run / f"{case_id}-attempt-1" / "qc" / "SCENARIO_GLOBAL.json",
    )


def preflight() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    from identity_restoration.application.benchmark_contract import load_benchmark_manifest
    from identity_restoration.application.benchmark_orchestration import _scenario_profile_id
    from validator_studio.schemas.face_validation import FaceValidationObservation
    from validator_studio.schemas.image_validation import ImageObservation

    manifest = load_benchmark_manifest(ROOT / "contracts/identity_restoration/benchmark_set.yaml")
    cases = {str(item["id"]): item for item in manifest["cases"]}
    model = os.environ.get("GEMINI_VISION_MODEL", "gemini-flash-latest")
    if model != "gemini-flash-latest":
        raise RuntimeError(f"PROVIDER_LOCK_MISMATCH: expected gemini-flash-latest, got {model}")
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        raise RuntimeError("AUTHORITATIVE_PROVIDER_NOT_CONFIGURED: Gemini credential is unavailable")
    if not A2_PATH.is_file() or sha_path(A2_PATH) != A2_SHA:
        raise RuntimeError("LINEAGE_UNPROVEN: A2 authority hash mismatch")

    lineage: list[dict[str, Any]] = []
    for case_id in CASES:
        job, candidate, face_input, placeholder = job_payload(case_id)
        if not all(path.is_file() for path in (candidate, face_input, placeholder)):
            raise RuntimeError(f"LINEAGE_UNPROVEN: incomplete {case_id} artifact set")
        expected_authority = "action_full_body@1.0" if case_id in {"B03", "B04"} else "canonical_default"
        authority = job["qualityScopes"]["SCENARIO_GLOBAL"]["authorityRef"]
        if authority["id"] != f"candidate-v3-{case_id}-" + ("action-full-body-1-0-v1" if case_id in {"B03", "B04"} else "canonical-default-v1"):
            raise RuntimeError(f"LINEAGE_UNPROVEN: {case_id} authority binding mismatch")
        if job.get("identityPackId") != "linh-an-production-v3-2026-08":
            raise RuntimeError(f"LINEAGE_UNPROVEN: {case_id} IdentityPack mismatch")
        lineage.append({
            "sampleId": case_id,
            "candidateArtifact": str(candidate.relative_to(ROOT)),
            "candidateArtifactSha256": sha_path(candidate),
            "faceInputArtifact": str(face_input.relative_to(ROOT)),
            "faceInputSha256": sha_path(face_input),
            "placeholderScenarioReport": str(placeholder.relative_to(ROOT)),
            "placeholderScenarioReportSha256": sha_path(placeholder),
            "authorityProfile": expected_authority,
            "validatorProfile": _scenario_profile_id(cases[case_id]),
            "allowedExclusions": ["shot_distance", "hairstyle"] if case_id in {"B03", "B04"} else [],
            "identityPackId": job["identityPackId"],
            "identityPackSha256": PACK_SHA,
            "referenceArtifacts": [{"path": str(A2_PATH.relative_to(ROOT)), "sha256": A2_SHA}],
            "lineageStatus": "VERIFIED",
        })
    return ({
        "schemaVersion": "candidate-v3-r1-p4-r1-preflight-1.0",
        "status": "PASS",
        "provider": "gemini",
        "model": model,
        "adapter": "VisionClient -> GeminiVisionProvider",
        "validatorEntrypoints": {
            "faceLocal": "validator_studio.face_validator.validate_face",
            "scenarioGlobal": "validator_studio.image_validator.validate_image",
        },
        "schemas": {
            "faceObservation": {"id": "FaceValidationObservation", "sha256": canonical_hash(FaceValidationObservation.model_json_schema())},
            "scenarioObservation": {"id": "ImageObservation", "sha256": canonical_hash(ImageObservation.model_json_schema())},
        },
        "samples": {"faceLocalPerCase": 3, "scenarioGlobalPerCase": 1, "logicalSamplesPlanned": 36},
        "retryPolicy": RETRY_POLICY,
        "circuitBreaker": {"threshold": 1, "scope": "run", "reset": "new resumable invocation only", "failClosed": True},
        "outputCap": 8192,
        "temperature": 0.0,
        "grounding": False,
        "credentials": "configured",
        "httpReadinessProbe": "not_performed",
        "lineage": "9/9 VERIFIED",
        "mockCalls": 0,
        "syntheticResults": 0,
        "gpuCalls": 0,
        "architectureChanged": False,
        "policyChanged": False,
        "workflowChanged": False,
        "identityPackChanged": False,
        "thresholdChanged": False,
    }, lineage)


def descriptor(lane: str, case_id: str, sample: int, artifact_sha: str, authority: str, profile: str, model: str) -> dict[str, Any]:
    return {
        "lane": lane, "sampleId": case_id, "sample": sample,
        "artifactSha256": artifact_sha,
        "referenceSha256": A2_SHA if lane == "FACE_LOCAL" else None,
        "authorityProfile": authority, "validatorProfile": profile,
        "provider": "gemini", "model": model,
        "validatorVersion": VALIDATOR_VERSION,
        "retryPolicy": RETRY_POLICY,
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows


def reusable_observation(lane: str, case_id: str, sample: int, desc: dict[str, Any], records: list[dict[str, Any]]) -> tuple[Any, dict[str, Any]] | None:
    """Reuse only a complete current-run record with all locked identity fields."""
    from shared.vision.structured import extract_json
    from validator_studio.face_validator import _assert_face_observation_contract, _load_face_rubric
    from validator_studio.schemas.face_validation import FaceValidationObservation
    from validator_studio.schemas.image_validation import ImageObservation

    expected_hash = canonical_hash(desc)
    for row in reversed(records):
        if row.get("requestHash") != expected_hash or row.get("status") != "VALID_RESPONSE":
            continue
        if any(row.get(key) != desc.get(key) for key in ("artifactSha256", "provider", "model", "validatorVersion", "authorityProfile", "validatorProfile")):
            continue
        raw_path = OUT / row["rawPath"]
        parsed_path = OUT / row["parsedPath"]
        if not raw_path.is_file() or not parsed_path.is_file() or sha_path(raw_path) != row.get("rawFileSha256"):
            continue
        try:
            payload = extract_json(raw_path.read_text(encoding="utf-8").rstrip("\n"))
            if lane == "FACE_LOCAL":
                _assert_face_observation_contract(payload, _load_face_rubric("venho_hotel"))
                observation = FaceValidationObservation.model_validate(payload)
            else:
                observation = ImageObservation.model_validate(payload)
        except Exception:
            continue
        if canonical_hash(observation.model_dump(mode="json")) != row.get("parsedResultHash"):
            continue
        return observation, {"lane": lane, "sampleId": case_id, "sample": sample, "requestHash": expected_hash, "source": row["rawPath"], "reason": "verified current-run response"}
    return None


def persist_event(lane: str, case_id: str, sample: int, desc: dict[str, Any], event: dict[str, Any]) -> None:
    append_jsonl(OUT / "attempt-history.jsonl", {"capturedAt": datetime.now(timezone.utc).isoformat(), "lane": lane, "sampleId": case_id, "sample": sample, **event})
    raw = event.get("rawResponse")
    if raw is None:
        return
    raw_text = str(raw).rstrip("\n")
    raw_path = OUT / "raw-provider" / lane / case_id / f"sample-{sample}.txt"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    if raw_path.exists() and raw_path.read_text(encoding="utf-8").rstrip("\n") != raw_text:
        raise RuntimeError(f"IMMUTABLE_RAW_EVIDENCE_CONFLICT: {raw_path}")
    if not raw_path.exists():
        raw_path.write_text(raw_text + "\n", encoding="utf-8")
    parsed = event.get("parsedEvidence")
    if parsed is not None:
        parsed_path = OUT / "parsed-provider" / lane / case_id / f"sample-{sample}.json"
        write_json(parsed_path, parsed)
        record = {
            **desc,
            "sample": sample,
            "requestHash": canonical_hash(desc),
            "status": "VALID_RESPONSE",
            "rawPath": str(raw_path.relative_to(OUT)),
            "rawResponseHash": sha_bytes(raw_text.encode()),
            "rawFileSha256": sha_path(raw_path),
            "parsedPath": str(parsed_path.relative_to(OUT)),
            "parsedResultHash": canonical_hash(parsed),
            "parsedFileSha256": sha_path(parsed_path),
            "attemptCount": int(event.get("transportAttemptIndex") or 1),
            "persistedAt": datetime.now(timezone.utc).isoformat(),
        }
        append_jsonl(OUT / "execution-manifest.jsonl", record)


def checkpoint(status: str, provider: dict[str, Any], face: list[dict[str, Any]], scenario: list[dict[str, Any]], boundary: dict[str, int], failure: Any = None) -> None:
    write_json(OUT / "checkpoint.json", {
        "roadmap": "candidate_v3_quality_remediation_r1",
        "task": "r1_p4_r1_provider_execution_remediation",
        "status": status,
        "provider": provider,
        "face_local": {"expected": 9, "valid": len(face), "disposition": "VALIDATED" if len(face) == 9 else "PROVIDER_BLOCKED"},
        "scenario_global": {"expected": 9, "valid": len(scenario), "disposition": "VALIDATED" if len(scenario) == 9 else "PROVIDER_BLOCKED"},
        "boundary": boundary,
        "gpu_calls": 0, "promotions": 0,
        "architecture_changed": False, "policy_changed": False, "workflow_changed": False,
        "identity_pack_changed": False, "threshold_changed": False,
        "failure": failure,
    })


def run() -> int:
    load_env()
    os.environ["VALIDATOR_LIVE_ENABLED"] = "true"
    os.environ["VALIDATOR_MAX_NEW_CALLS"] = "36"
    os.environ["VALIDATOR_PAID_CALL_LEDGER"] = str(OUT / "provider-paid-call-ledger.jsonl")
    OUT.mkdir(parents=True, exist_ok=True)

    try:
        preflight_report, lineage = preflight()
    except Exception as exc:
        write_json(OUT / "preflight.json", {"status": "BLOCKED", "error": str(exc), "providerCalls": 0, "gpuCalls": 0})
        checkpoint("PROVIDER_BLOCKED", {"name": "gemini", "model": "gemini-flash-latest", "calls_this_task": 0, "reused_valid_calls": 0, "successful_calls": 0, "failed_calls": 0, "retryable_503": 0}, [], [], {"pass": 0, "fail": 0}, str(exc))
        raise
    write_json(OUT / "preflight.json", preflight_report)
    write_json(OUT / "lineage-manifest.json", {"status": "VERIFIED", "rows": lineage})
    write_json(OUT / "adapter-audit.json", {
        "provider": "gemini", "model": "gemini-flash-latest",
        "classification": "503/UNAVAILABLE -> PROVIDER_503; 429/RESOURCE_EXHAUSTED -> PROVIDER_429; timeout -> PROVIDER_TIMEOUT",
        "existingRetry": RETRY_POLICY,
        "requestIdempotency": "safe at logical-sample level; each retry is separately guarded/ledgered",
        "circuitBreaker": "ProviderCircuitBreaker opens fail-closed after one terminal retryable logical-sample failure; no in-run reset; a new resume invocation is the reset boundary",
        "persistence": "append-only attempt-history plus execution-manifest after schema-valid response",
        "resume": "completed response is reusable only when request/artifact/provider/model/validator/authority hashes and files verify",
        "rootCause": "R1-P4 orchestration had hard-coded B01 reuse and no general checkpoint/reuse contract; Gemini 503 remains provider availability, not payload defect",
        "remediation": "runner-only; provider adapter, rubric, thresholds, authority, architecture unchanged",
    })

    from identity_restoration.application.benchmark_contract import load_benchmark_manifest
    from identity_restoration.application.benchmark_orchestration import _scenario_profile_id
    from shared.vision.paid_call_guard import paid_call_context
    from shared.vision.providers.gemini_vision import ProviderCircuitBreaker, classify_gemini_failure
    from validator_studio.face_validator import _assert_face_observation_contract, _load_face_rubric, report_from_face_observations, validate_face
    from validator_studio.image_validator import report_from_image_observations, validate_image
    from validator_studio.schemas.face_validation import FaceValidationObservation
    from validator_studio.schemas.image_validation import ImageObservation
    from shared.vision.structured import extract_json

    manifest = load_benchmark_manifest(ROOT / "contracts/identity_restoration/benchmark_set.yaml")
    cases = {str(item["id"]): item for item in manifest["cases"]}
    records = read_jsonl(OUT / "execution-manifest.jsonl")
    face_results: list[dict[str, Any]] = []
    scenario_results: list[dict[str, Any]] = []
    reused: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    breaker = ProviderCircuitBreaker()
    provider_stats = {"name": "gemini", "model": preflight_report["model"], "calls_this_task": 0, "reused_valid_calls": 0, "successful_calls": 0, "failed_calls": 0, "retryable_503": 0}

    def run_one(lane: str, case_id: str, sample: int, image_path: Path, authority: str, profile: str) -> Any:
        desc = descriptor(lane, case_id, sample, sha_path(image_path), authority, profile, preflight_report["model"])
        hit = reusable_observation(lane, case_id, sample, desc, records)
        if hit is not None:
            reused.append(hit[1])
            provider_stats["reused_valid_calls"] += 1
            return hit[0]
        if breaker.opened:
            raise RuntimeError(f"PROVIDER_BLOCKED_BEFORE_REQUEST: {breaker.failure_class}")
        state: dict[str, Any] = {}
        def sink(event: dict[str, Any]) -> None:
            state.update({key: value for key, value in event.items() if key in {"rawResponse", "parseStatus", "transportAttemptIndex"}})
            persist_event(lane, case_id, sample, desc, event)
        try:
            with paid_call_context({
                "benchmarkId": "candidate-v3-r1-p4-r1",
                "branch": lane,
                "imageSha256": sha_path(image_path),
                "sampleIndex": sample,
                "reason": "R1-P4-R1 provider execution remediation",
                "historicalEvidenceSearch": {"exactArtifactCacheMatch": False, "lineage": "VERIFIED"},
            }):
                if lane == "FACE_LOCAL":
                    report = validate_face("venho_hotel", "linh_an", image_path, provider="gemini", reference_image_paths=[A2_PATH], samples=1, raw_response_sink=sink, validation_cycle_id=f"candidate-v3-r1-p4-r1-{case_id.lower()}-face-{sample}", attempt_id="r1-p4-r1")
                    return FaceValidationObservation.model_validate(report.raw_observation)
                report = validate_image("venho_hotel", "linh_an", image_path, provider="gemini", samples=1, scenario_profile_id=profile, raw_response_sink=sink)
                return ImageObservation.model_validate(report.raw_observation)
        except Exception as exc:
            classification = classify_gemini_failure(exc)
            breaker.record(exc)
            failures.append({"lane": lane, "sampleId": case_id, "sample": sample, "classification": classification, "error": str(exc), "attemptHistory": [event for event in read_jsonl(OUT / "attempt-history.jsonl") if event.get("lane") == lane and event.get("sampleId") == case_id and event.get("sample") == sample]})
            raise
        finally:
            ledger_rows = read_jsonl(OUT / "provider-paid-call-ledger.jsonl")
            result_rows = [row for row in ledger_rows if row.get("event") == "result"]
            provider_stats["calls_this_task"] = len([row for row in ledger_rows if row.get("event") == "intent"])
            provider_stats["successful_calls"] = len([row for row in result_rows if row.get("success") is True])
            provider_stats["failed_calls"] = len([row for row in result_rows if row.get("success") is False])
            provider_stats["retryable_503"] = sum("503" in str(row.get("error", "")) or row.get("httpStatus") == 503 for row in result_rows)

    def save_progress(failure: Any = None) -> None:
        boundary_rows = json.loads((P1 / "per-sample-results.json").read_text(encoding="utf-8"))["samples"]
        boundary = {"pass": sum(row["postRemediation"]["status"] == "PASS" for row in boundary_rows), "fail": sum(row["postRemediation"]["status"] != "PASS" for row in boundary_rows)}
        checkpoint("PROVIDER_BLOCKED" if failure else "IN_PROGRESS", provider_stats, face_results, scenario_results, boundary, failure)

    try:
        for row in lineage:
            case_id = row["sampleId"]
            candidate = ROOT / row["candidateArtifact"]
            face_input = ROOT / row["faceInputArtifact"]
            profile = _scenario_profile_id(cases[case_id])
            observations: list[FaceValidationObservation] = []
            for sample in range(1, 4):
                observations.append(run_one("FACE_LOCAL", case_id, sample, face_input, row["authorityProfile"], profile))
                save_progress()
            face_report = report_from_face_observations("venho_hotel", "linh_an", face_input, observations, provider="gemini", reference_image_paths=[A2_PATH])
            face_data = face_report.model_dump(mode="json")
            face_results.append({"sampleId": case_id, "lane": "FACE_LOCAL", "artifactSha256": sha_path(face_input), "quality": face_data, "qualityPass": float(face_data["overall_score"]) >= 90.0})
            save_progress()
            scenario_observation = run_one("SCENARIO_GLOBAL", case_id, 1, candidate, row["authorityProfile"], profile)
            scenario_report = report_from_image_observations("venho_hotel", "linh_an", candidate, [scenario_observation], provider="gemini", scenario_profile_id=profile)
            scenario_data = scenario_report.model_dump(mode="json")
            scenario_results.append({"sampleId": case_id, "lane": "SCENARIO_GLOBAL", "artifactSha256": sha_path(candidate), "authorityProfile": row["authorityProfile"], "quality": scenario_data, "qualityPass": float(scenario_data["overall_score"]) >= 90.0})
            save_progress()
    except Exception as exc:
        save_progress(str(exc))

    lane_status = "VALIDATED" if len(face_results) == 9 else "PROVIDER_BLOCKED"
    scenario_status = "VALIDATED" if len(scenario_results) == 9 else "PROVIDER_BLOCKED"
    overall = "PASS" if lane_status == "VALIDATED" and scenario_status == "VALIDATED" else "PROVIDER_BLOCKED"
    write_json(OUT / "reused-response-manifest.json", {"reusedValidCalls": len(reused), "reused": reused, "rejectedHistoricalR1P4": [{"source": "r1-p4-authoritative-validation-20260901-final/raw-evidence-index.json", "reason": "missing requestHash, validatorVersion, and policy lineage; not reusable under R1-P4-R1"}]})
    write_json(OUT / "FACE_LOCAL.json", {"scope": "FACE_LOCAL", "status": lane_status, "expected": 9, "evaluated": len(face_results), "valid": len(face_results), "qualityPass": sum(item["qualityPass"] for item in face_results) if len(face_results) == 9 else None, "qualityFail": sum(not item["qualityPass"] for item in face_results) if len(face_results) == 9 else None, "results": face_results, "failures": failures})
    write_json(OUT / "SCENARIO_GLOBAL.json", {"scope": "SCENARIO_GLOBAL", "status": scenario_status, "expected": 9, "evaluated": len(scenario_results), "valid": len(scenario_results), "qualityPass": sum(item["qualityPass"] for item in scenario_results) if len(scenario_results) == 9 else None, "qualityFail": sum(not item["qualityPass"] for item in scenario_results) if len(scenario_results) == 9 else None, "results": scenario_results, "failures": failures})
    boundary_rows = json.loads((P1 / "per-sample-results.json").read_text(encoding="utf-8"))["samples"]
    boundary = {"pass": sum(row["postRemediation"]["status"] == "PASS" for row in boundary_rows), "fail": sum(row["postRemediation"]["status"] != "PASS" for row in boundary_rows)}
    ledger_rows = read_jsonl(OUT / "provider-paid-call-ledger.jsonl")
    provider_manifest = {"provider": "gemini", "model": preflight_report["model"], "calls": len([row for row in ledger_rows if row.get("event") == "intent"]), "successfulCalls": len([row for row in ledger_rows if row.get("event") == "result" and row.get("success") is True]), "failedCalls": len([row for row in ledger_rows if row.get("event") == "result" and row.get("success") is False]), "reusedValidCalls": len(reused), "logicalSamplesCompleted": len(face_results) * 3 + len(scenario_results), "retryPolicy": RETRY_POLICY, "circuitBreaker": {"activated": breaker.opened, "failureClass": breaker.failure_class, "providerAvailability": breaker.provider_availability}, "gpuCalls": 0, "mockCalls": 0, "syntheticResults": 0, "promotions": 0, "failures": failures}
    write_json(OUT / "execution-manifest.json", {"schemaVersion": "candidate-v3-r1-p4-r1-execution-manifest-1.0", "provider": "gemini", "model": preflight_report["model"], "status": overall, "calls": provider_manifest["calls"], "successfulCalls": provider_manifest["successfulCalls"], "failedCalls": provider_manifest["failedCalls"], "reusedValidCalls": len(reused), "logicalSamplesCompleted": provider_manifest["logicalSamplesCompleted"], "records": read_jsonl(OUT / "execution-manifest.jsonl")})
    checkpoint(overall, provider_stats, face_results, scenario_results, boundary, failures[-1] if failures else None)
    write_json(OUT / "provider-call-manifest.json", provider_manifest)
    write_json(OUT / "checkpoint.json", {**json.loads((OUT / "checkpoint.json").read_text(encoding="utf-8")), "status": overall, "provider": {**provider_stats, "calls": provider_manifest["calls"], "successful_calls": provider_manifest["successfulCalls"], "failed_calls": provider_manifest["failedCalls"]}})
    (OUT / "root-cause-report.md").write_text(
        "# R1-P4-R1 Provider Execution Remediation\n\n"
        f"Status: `{overall}`. Provider lock remained Gemini `{preflight_report['model']}`.\n\n"
        "The adapter already classified 503 as `PROVIDER_503` and applied two bounded transport attempts with 0.25 second backoff and no jitter. The deterministic defect was in the prior orchestration: reuse was hard-coded to one sample and lacked request/validator/policy metadata, so completed work could not be resumed generically. This runner persists attempt history and each schema-valid response before advancing, and resumes only after exact metadata/hash verification.\n\n"
        f"The R1-P4 historical response was not reused because its evidence lacks the required request hash, validator version, and policy lineage. Provider calls in this task: `{provider_manifest['calls']}`; successful: `{provider_manifest['successfulCalls']}`; failed: `{provider_manifest['failedCalls']}`.\n\n"
        "No quality logic, rubric, threshold, authority, model alias, architecture, workflow, IdentityPack, GPU path, generation, mock, synthetic result, or promotion was changed.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUT.rglob("*")) if path.is_file() and path.name != "sha256.json"]
    hashes = {str(path.relative_to(OUT)): sha_path(path) for path in files}
    write_json(OUT / "sha256.json", {"algorithm": "SHA-256", "files": hashes, "count": len(hashes)})
    print(json.dumps({"status": overall, "output": str(OUT), "providerCalls": provider_manifest["calls"], "successfulCalls": provider_manifest["successfulCalls"], "failedCalls": provider_manifest["failedCalls"], "reusedValidCalls": len(reused), "faceLocal": len(face_results), "scenarioGlobal": len(scenario_results), "boundary": f"{boundary['pass']}/{boundary['pass'] + boundary['fail']}"}, ensure_ascii=False))
    return 0 if overall == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(run())
