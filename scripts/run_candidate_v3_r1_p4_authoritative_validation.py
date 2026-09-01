#!/usr/bin/env python3
"""Run the authorized Candidate v3 R1-P4 validation lanes on existing artifacts.

This runner never invokes the restoration bridge.  It validates the immutable
R1-P1 composite outputs and their existing canonical crops through the
repository's configured Gemini Validator Studio adapter only.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/identity-restoration/phase7-candidate-v3/r1-p4-authoritative-validation-20260901-r2"
PREVIOUS_OUT = ROOT / "artifacts/identity-restoration/phase7-candidate-v3/r1-p4-authoritative-validation-20260901"
P1 = ROOT / "artifacts/identity-restoration/phase7-candidate-v3/r1-p1-boundary-remediation-20260828"
PHASE7 = ROOT / "artifacts/identity-restoration/phase7-candidate-v3"
PACK_PATH = ROOT / "config/identity_restoration/identity_packs/linh-an-production-v3-2026-08.json"
A2_PATH = ROOT / "assets/linh_an/A2_Front.png"
DNA_PATH = ROOT / "data/projects/venho_hotel/knowledge/VENHO_HOTEL_LINH_AN_DNA.json"
RUBRIC_PATH = ROOT / "config/projects/venho_hotel/face_qc_rubric.yaml"
LEDGER = OUT / "provider-paid-call-ledger.jsonl"
WORKFLOW_SHA = "53dc090691b8feac2a8b8a4309d43af737e304b09330e072b4ab5632ed5aad91"
PACK_SHA = "fc185a9e47a33092fbafe357a140b65f9449bac0de28d7e20b9f33d8ddcbb406"
A2_SHA = "1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d"
PROFILE_SHA = {
    "canonical_default": "71f839dff776ec6d6d085c5a1ab928295af8c32a9699f7929d78b04807ec0075",
    "action_full_body@1.0": "fe4a2b454a5868e9fc4dfbc4216e413a69a186cc8b4ab89c066943843c869b1c",
}
CASES = tuple(f"B{i:02d}" for i in range(1, 10))


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_path(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def canonical_hash(value: Any) -> str:
    return sha_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def load_env() -> None:
    social = ROOT.parent.parent / "venho-social-content-agent"
    for path in (social / ".env.local", social / ".env", ROOT / ".env.local", ROOT / ".env"):
        if path.is_file():
            load_dotenv(path, override=False)


def job_payload(case_id: str) -> tuple[dict[str, Any], Path, Path, Path]:
    number = int(case_id[1:])
    run = "phase7-benchmark-20260828" if number <= 4 or number >= 7 else "phase7-diagnostic-20260828"
    job_path = PHASE7 / "jobs" / f"{run}-{case_id}.json"
    job = json.loads(job_path.read_text(encoding="utf-8"))
    candidate = P1 / case_id / "inverse-composite-remediated.png"
    face_input = PHASE7 / run / f"{case_id}-attempt-1" / "restored-canonical.png"
    scenario_report = PHASE7 / run / f"{case_id}-attempt-1" / "qc" / "SCENARIO_GLOBAL.json"
    return job, candidate, face_input, scenario_report


def preflight() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    from identity_restoration.application.benchmark_orchestration import _scenario_profile_id
    from identity_restoration.application.benchmark_contract import load_benchmark_manifest
    from validator_studio.schemas.face_validation import FaceValidationObservation
    from validator_studio.schemas.image_validation import ImageObservation

    manifest = load_benchmark_manifest(ROOT / "contracts/identity_restoration/benchmark_set.yaml")
    cases = {str(item["id"]): item for item in manifest["cases"]}
    model = os.environ.get("GEMINI_VISION_MODEL", "gemini-flash-latest")
    credential_configured = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    if sha_path(A2_PATH) != A2_SHA:
        raise RuntimeError("LINEAGE_UNPROVEN: A2 authority hash mismatch")
    if not PACK_PATH.is_file() or not DNA_PATH.is_file() or not RUBRIC_PATH.is_file():
        raise RuntimeError("LINEAGE_UNPROVEN: validator authority file is missing")
    if not credential_configured:
        raise RuntimeError("AUTHORITATIVE_PROVIDER_NOT_CONFIGURED: Gemini credential is unavailable")

    lineage: list[dict[str, Any]] = []
    for case_id in CASES:
        job, candidate, face_input, scenario_report = job_payload(case_id)
        if not all(path.is_file() for path in (candidate, face_input, scenario_report)):
            raise RuntimeError(f"LINEAGE_UNPROVEN: incomplete {case_id} artifact set")
        scope = job["qualityScopes"]["SCENARIO_GLOBAL"]["authorityRef"]
        profile = str(job["qualityScopes"]["SCENARIO_GLOBAL"]["authorityRef"]["id"])
        expected_profile = "action_full_body@1.0" if case_id in {"B03", "B04"} else "canonical_default"
        if scope["sha256"] != PROFILE_SHA[expected_profile]:
            raise RuntimeError(f"LINEAGE_UNPROVEN: {case_id} scenario authority hash mismatch")
        if profile != f"candidate-v3-{case_id}-" + ("action-full-body-1-0-v1" if case_id in {"B03", "B04"} else "canonical-default-v1"):
            raise RuntimeError(f"LINEAGE_UNPROVEN: {case_id} binding mismatch")
        workflow = job["lineage"]["bridge"]["adapterEvidence"]["workflowSha256"]
        if workflow != WORKFLOW_SHA or job["identityPackId"] != "linh-an-production-v3-2026-08":
            raise RuntimeError(f"LINEAGE_UNPROVEN: {case_id} workflow or IdentityPack mismatch")
        validator_profile = _scenario_profile_id(cases[case_id])
        lineage.append({
            "sampleId": case_id,
            "candidateArtifact": str(candidate.relative_to(ROOT)),
            "candidateArtifactSha256": sha_path(candidate),
            "faceInputArtifact": str(face_input.relative_to(ROOT)),
            "faceInputSha256": sha_path(face_input),
            "placeholderScenarioReport": str(scenario_report.relative_to(ROOT)),
            "placeholderScenarioReportSha256": sha_path(scenario_report),
            "scenarioId": case_id,
            "scenarioProfile": expected_profile,
            "validatorLookupProfile": validator_profile,
            "authorityProfile": expected_profile,
            "allowedExclusions": ["shot_distance", "hairstyle"] if case_id in {"B03", "B04"} else [],
            "workflowSha256": workflow,
            "identityPackId": job["identityPackId"],
            "identityPackSha256": PACK_SHA,
            "requiredReferenceArtifacts": [{"path": str(A2_PATH.relative_to(ROOT)), "sha256": A2_SHA}],
            "lineageStatus": "VERIFIED",
        })

    preflight_report = {
        "schemaVersion": "candidate-v3-r1-p4-preflight-1.0",
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
        "retry": {"maxTransportAttemptsPerLogicalSample": 2, "retryable": ["PROVIDER_503", "PROVIDER_429", "PROVIDER_TIMEOUT"]},
        "outputCap": 8192,
        "temperature": 0.0,
        "grounding": False,
        "credentials": "configured",
        "httpReadinessProbe": "not_performed",
        "gpuCalls": 0,
        "lineageVerified": True,
        "thresholdsChanged": False,
        "validatorBypassed": False,
    }
    return preflight_report, lineage


def event_sink(lane: str, case_id: str, state: dict[str, Any], sample_override: int | None = None) -> Callable[[dict[str, Any]], None]:
    def sink(event: dict[str, Any]) -> None:
        state["events"].append(dict(event))
        sample = sample_override or int(event.get("logicalSampleIndex") or event.get("sampleIndex") or 0)
        if event.get("rawResponse") is not None:
            raw = str(event["rawResponse"])
            raw_hash = sha_bytes(raw.encode())
            state["rawHashes"][sample] = raw_hash
            path = OUT / "raw-provider" / lane / case_id / f"sample-{sample}.txt"
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists() and path.read_text(encoding="utf-8").rstrip("\n") != raw:
                raise RuntimeError(f"IMMUTABLE_RAW_EVIDENCE_CONFLICT: {path}")
            if not path.exists():
                path.write_text(raw + "\n", encoding="utf-8")
        if event.get("parsedEvidence") is not None:
            parsed = event["parsedEvidence"]
            parsed_hash = canonical_hash(parsed)
            state["parsedHashes"][sample] = parsed_hash
            write_json(OUT / "parsed-provider" / lane / case_id / f"sample-{sample}.json", parsed)
    return sink


def run() -> int:
    sys.path.insert(0, str(ROOT))
    load_env()
    os.environ["VALIDATOR_LIVE_ENABLED"] = "true"
    os.environ["VALIDATOR_MAX_NEW_CALLS"] = "36"
    os.environ["VALIDATOR_PAID_CALL_LEDGER"] = str(LEDGER)
    OUT.mkdir(parents=True, exist_ok=False)

    try:
        preflight_report, lineage = preflight()
    except Exception as exc:
        OUT.mkdir(parents=True, exist_ok=True)
        write_json(OUT / "preflight.json", {"status": "BLOCKED", "error": str(exc), "providerCalls": 0, "gpuCalls": 0})
        write_json(OUT / "r1-p4-checkpoint.json", {"roadmap": "candidate_v3_quality_remediation_r1", "task": "r1_p4_authoritative_provider_validation", "status": "BLOCKED", "gpu_calls": 0, "provider_calls": 0, "blocker": str(exc)})
        raise

    write_json(OUT / "preflight.json", preflight_report)
    write_json(OUT / "lineage-manifest.json", {"schemaVersion": "candidate-v3-r1-p4-lineage-1.0", "status": "VERIFIED", "identityPackSha256": PACK_SHA, "rows": lineage})

    from identity_restoration.application.benchmark_orchestration import _scenario_profile_id
    from identity_restoration.application.benchmark_contract import load_benchmark_manifest
    from validator_studio.face_validator import (
        _assert_face_observation_contract,
        _load_face_rubric,
        report_from_face_observations,
        validate_face,
    )
    from validator_studio.image_validator import validate_image
    from validator_studio.schemas.face_validation import FaceValidationObservation
    from shared.vision.structured import extract_json

    manifest = load_benchmark_manifest(ROOT / "contracts/identity_restoration/benchmark_set.yaml")
    cases = {str(item["id"]): item for item in manifest["cases"]}
    face_results: list[dict[str, Any]] = []
    scenario_results: list[dict[str, Any]] = []
    failure: dict[str, Any] | None = None

    for row in lineage:
        case_id = row["sampleId"]
        candidate = ROOT / row["candidateArtifact"]
        face_input = ROOT / row["faceInputArtifact"]
        profile = _scenario_profile_id(cases[case_id])
        for lane in ("FACE_LOCAL", "SCENARIO_GLOBAL"):
            state: dict[str, Any] = {"events": [], "rawHashes": {}, "parsedHashes": {}}
            image_path = face_input if lane == "FACE_LOCAL" else candidate
            samples = 3 if lane == "FACE_LOCAL" else 1
            descriptor = {
                "lane": lane,
                "sampleId": case_id,
                "artifactSha256": sha_path(image_path),
                "referenceSha256": A2_SHA if lane == "FACE_LOCAL" else None,
                "scenarioProfile": row["authorityProfile"],
                "validatorProfile": profile,
                "provider": "gemini",
                "model": preflight_report["model"],
                "samples": samples,
            }
            try:
                if lane == "FACE_LOCAL":
                    observations: list[FaceValidationObservation] = []
                    for sample_index in range(1, samples + 1):
                        previous_raw = PREVIOUS_OUT / "raw-provider" / lane / case_id / f"sample-{sample_index}.txt"
                        if case_id == "B01" and sample_index == 1 and previous_raw.is_file():
                            raw = previous_raw.read_text(encoding="utf-8").rstrip("\n")
                            payload = extract_json(raw)
                            _assert_face_observation_contract(payload, _load_face_rubric("venho_hotel"))
                            observation = FaceValidationObservation.model_validate(payload)
                            state["rawHashes"][sample_index] = sha_bytes(raw.encode())
                            state["parsedHashes"][sample_index] = canonical_hash(payload)
                            target_raw = OUT / "raw-provider" / lane / case_id / f"sample-{sample_index}.txt"
                            target_raw.parent.mkdir(parents=True, exist_ok=True)
                            target_raw.write_text(raw + "\n", encoding="utf-8")
                            write_json(OUT / "parsed-provider" / lane / case_id / f"sample-{sample_index}.json", payload)
                            observations.append(observation)
                            state.setdefault("reusedSamples", []).append({"sample": sample_index, "source": str(previous_raw.relative_to(ROOT))})
                            continue
                        with __import__("shared.vision.paid_call_guard", fromlist=["paid_call_context"]).paid_call_context({
                            "benchmarkId": "candidate-v3-r1-p4",
                            "branch": lane,
                            "imageSha256": sha_path(image_path),
                            "sampleIndex": sample_index,
                            "reason": "R1-P4 authoritative validation of existing Candidate v3 artifact",
                            "historicalEvidenceSearch": {"exactArtifactCacheMatch": False, "lineage": "VERIFIED"},
                        }):
                            one = validate_face(
                                "venho_hotel", "linh_an", image_path, provider="gemini",
                                reference_image_paths=[A2_PATH], samples=1,
                                raw_response_sink=event_sink(lane, case_id, state, sample_override=sample_index),
                                validation_cycle_id=f"candidate-v3-r1-p4-{case_id.lower()}-face-{sample_index}",
                                attempt_id="r1-p4",
                            )
                        observations.append(FaceValidationObservation.model_validate(one.raw_observation))
                    report = report_from_face_observations(
                        "venho_hotel", "linh_an", image_path, observations,
                        provider="gemini", reference_image_paths=[A2_PATH],
                    )
                else:
                    with __import__("shared.vision.paid_call_guard", fromlist=["paid_call_context"]).paid_call_context({
                        "benchmarkId": "candidate-v3-r1-p4",
                        "branch": lane,
                        "imageSha256": sha_path(image_path),
                        "sampleIndex": 1,
                        "reason": "R1-P4 authoritative validation of existing Candidate v3 artifact",
                        "historicalEvidenceSearch": {"exactArtifactCacheMatch": False, "lineage": "VERIFIED"},
                    }):
                        report = validate_image(
                            "venho_hotel", "linh_an", image_path, provider="gemini", samples=1,
                            scenario_profile_id=profile,
                            raw_response_sink=event_sink(lane, case_id, state, sample_override=1),
                        )
                report_data = report.model_dump(mode="json")
                score = float(report.overall_score)
                passed = score >= 90.0
                result = {
                    **descriptor,
                    "requestHash": canonical_hash(descriptor),
                    "artifactSha256": sha_path(image_path),
                    "validatorVersion": "validator-studio-existing-production-entrypoint",
                    "report": report_data,
                    "score": score,
                    "passed": passed,
                    "failureReasons": [str(item.get("issue", item)) for item in report_data.get("issues", [])],
                    "rawResponseHashes": {str(k): v for k, v in sorted(state["rawHashes"].items())},
                    "parsedResultHashes": {str(k): v for k, v in sorted(state["parsedHashes"].items())},
                    "parsedResultHash": canonical_hash(report_data),
                    "reusedProviderSamples": state.get("reusedSamples", []),
                }
                if len(state["rawHashes"]) != samples or len(state["parsedHashes"]) != samples:
                    raise RuntimeError(f"INCOMPLETE_PROVIDER_EVIDENCE: {lane}/{case_id}")
                (face_results if lane == "FACE_LOCAL" else scenario_results).append(result)
            except Exception as exc:
                failure = {"lane": lane, "sampleId": case_id, "classification": "PROVIDER_BLOCKED", "error": str(exc)}
                break
        if failure:
            break

    ledger_rows = []
    if LEDGER.is_file():
        ledger_rows = [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines() if line.strip()]
    intents = [item for item in ledger_rows if item.get("event") == "intent"]
    results = [item for item in ledger_rows if item.get("event") == "result"]
    successful = [item for item in results if item.get("success") is True]
    failed = [item for item in results if item.get("success") is False]
    provider_manifest = {
        "schemaVersion": "candidate-v3-r1-p4-provider-calls-1.0",
        "provider": "gemini",
        "model": preflight_report["model"],
        "logicalSamples": len(face_results) * 3 + len(scenario_results),
        "calls": len(intents),
        "successfulCalls": len(successful),
        "failedCalls": len(failed),
        "inputTokens": sum(int(item.get("inputTokens") or 0) for item in results),
        "outputTokens": sum(int(item.get("outputTokens") or 0) for item in results),
        "estimatedCost": None,
        "retryPolicy": preflight_report["retry"],
        "ledger": str(LEDGER.relative_to(ROOT)),
        "failure": failure,
    }
    write_json(OUT / "provider-call-manifest.json", provider_manifest)
    write_json(OUT / "FACE_LOCAL.json", {"scope": "FACE_LOCAL", "status": "PASS" if not failure and len(face_results) == 9 else "PROVIDER_BLOCKED", "expected": 9, "evaluated": len(face_results), "valid": len(face_results), "qualityPass": sum(item["passed"] for item in face_results) if len(face_results) == 9 else None, "qualityFail": sum(not item["passed"] for item in face_results) if len(face_results) == 9 else None, "results": face_results})
    write_json(OUT / "SCENARIO_GLOBAL.json", {"scope": "SCENARIO_GLOBAL", "status": "PASS" if not failure and len(scenario_results) == 9 else "PROVIDER_BLOCKED", "expected": 9, "evaluated": len(scenario_results), "valid": len(scenario_results), "qualityPass": sum(item["passed"] for item in scenario_results) if len(scenario_results) == 9 else None, "qualityFail": sum(not item["passed"] for item in scenario_results) if len(scenario_results) == 9 else None, "results": scenario_results})

    boundary = json.loads((P1 / "per-sample-results.json").read_text(encoding="utf-8"))
    boundary_pass = sum(row["postRemediation"]["status"] == "PASS" for row in boundary["samples"])
    checkpoint_status = "PASS" if not failure and len(face_results) == 9 and len(scenario_results) == 9 else "PROVIDER_BLOCKED"
    checkpoint = {
        "roadmap": "candidate_v3_quality_remediation_r1",
        "task": "r1_p4_authoritative_provider_validation",
        "status": checkpoint_status,
        "gpu_calls": 0,
        "provider_calls": len(intents),
        "boundary": {"pass": boundary_pass, "fail": len(boundary["samples"]) - boundary_pass},
        "face_local": {"expected": 9, "evaluated": len(face_results), "valid": len(face_results), "quality_pass": sum(item["passed"] for item in face_results) if len(face_results) == 9 else None, "quality_fail": sum(not item["passed"] for item in face_results) if len(face_results) == 9 else None, "disposition": "VALIDATED" if len(face_results) == 9 else "PROVIDER_BLOCKED"},
        "scenario_global": {"expected": 9, "evaluated": len(scenario_results), "valid": len(scenario_results), "quality_pass": sum(item["passed"] for item in scenario_results) if len(scenario_results) == 9 else None, "quality_fail": sum(not item["passed"] for item in scenario_results) if len(scenario_results) == 9 else None, "disposition": "VALIDATED" if len(scenario_results) == 9 else "PROVIDER_BLOCKED"},
        "provider": {"name": "gemini", "model": preflight_report["model"], "calls": len(intents), "successful_calls": len(successful), "failed_calls": len(failed), "input_tokens": provider_manifest["inputTokens"], "output_tokens": provider_manifest["outputTokens"], "estimated_cost": None},
        "failure": failure,
        "architecture_changed": False,
        "policy_changed": False,
        "workflow_changed": False,
        "identity_pack_changed": False,
        "production_promotion": False,
    }
    write_json(OUT / "r1-p4-checkpoint.json", checkpoint)
    print(json.dumps({"status": checkpoint_status, "providerCalls": len(intents), "successfulCalls": len(successful), "failedCalls": len(failed), "faceLocal": len(face_results), "scenarioGlobal": len(scenario_results), "boundary": f"{boundary_pass}/{len(boundary['samples'])}"}, ensure_ascii=False))
    return 0 if checkpoint_status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(run())
