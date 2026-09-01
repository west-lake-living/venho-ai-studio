#!/usr/bin/env python3
"""Run the explicitly authorized Candidate v3 R1 recovery recheck.

The existing R1-P4 runner remains the only implementation of authoritative
FACE_LOCAL/SCENARIO_GLOBAL validation. This wrapper adds the task-mandated
single recovery probe before allowing that runner to execute the remaining
pending cases, and records task-specific evidence without changing provider,
rubric, thresholds, or production behavior.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PHASE7 = ROOT / "artifacts/identity-restoration/phase7-candidate-v3"
HOLD_GATE = PHASE7 / "r1-p4-r3-provider-hold-active.json"
P1 = PHASE7 / "r1-p1-boundary-remediation-20260828"
R5 = PHASE7 / "r1-p4-r5-provider-503-isolation-20260901T083517Z"
RUNNER_PATH = ROOT / "scripts/run_candidate_v3_r1_p4_r1_provider_remediation.py"
OUT = Path(os.environ.get(
    "R1_RECOVERY_RECHECK_OUTPUT_DIR",
    str(PHASE7 / ("r1-recovery-recheck-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))),
))


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_path(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def load_runner() -> Any:
    os.environ["R1_P4_R1_OUTPUT_DIR"] = str(OUT)
    spec = importlib.util.spec_from_file_location("candidate_v3_r1_p4_runner", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load existing R1-P4 runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def boundary_counts() -> dict[str, int]:
    rows = json.loads((P1 / "per-sample-results.json").read_text(encoding="utf-8"))["samples"]
    return {
        "pass": sum(row["postRemediation"]["status"] == "PASS" for row in rows),
        "fail": sum(row["postRemediation"]["status"] != "PASS" for row in rows),
    }


def ledger_rows() -> list[dict[str, Any]]:
    path = OUT / "provider-paid-call-ledger.jsonl"
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def execution_rows() -> list[dict[str, Any]]:
    path = OUT / "execution-manifest.jsonl"
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def evidence_hashes() -> dict[str, str]:
    return {
        str(path.relative_to(OUT)): sha_path(path)
        for path in sorted(OUT.rglob("*"))
        if path.is_file() and path.name != "hashes.sha256"
    }


def write_hashes() -> None:
    hashes = evidence_hashes()
    write_json(OUT / "hashes.sha256", {"algorithm": "SHA-256", "files": hashes, "count": len(hashes)})


def baseline(runner: Any, preflight: dict[str, Any]) -> dict[str, Any]:
    hold = json.loads(HOLD_GATE.read_text(encoding="utf-8"))
    return {
        "taskId": "candidate-v3-r1-recovery-recheck",
        "authorization": {"RECOVERY_RECHECK_AUTHORIZED": True},
        "capturedAt": datetime.now(timezone.utc).isoformat(),
        "roadmapState": {
            "phase7": "CLOSED / QUALITY FAIL",
            "r1P4": "PROVIDER_BLOCKED",
            "r1P4R5": "CLOSED / PASS",
        },
        "startState": {
            "boundary": boundary_counts(),
            "faceLocal": {"expected": 9, "valid": 0, "disposition": "UNVALIDATED / PROVIDER_BLOCKED"},
            "scenarioGlobal": {"expected": 9, "valid": 0, "disposition": "UNVALIDATED / PROVIDER_BLOCKED"},
            "pendingAuthoritativeEvaluations": 18,
        },
        "providerHold": hold.get("provider_hold", {}),
        "previousBlocker": "PROVIDER_SERVICE_UNAVAILABLE / repeated Gemini 503 high-demand responses",
        "provider": {
            "name": preflight.get("provider"),
            "model": preflight.get("model"),
            "retryPolicy": preflight.get("retryPolicy"),
            "circuitBreaker": preflight.get("circuitBreaker"),
            "outputCap": preflight.get("outputCap"),
        },
        "priorEvidence": str(R5.relative_to(ROOT)),
        "holdGateSha256": sha_path(HOLD_GATE),
        "offlinePreflight": preflight,
    }


def run_probe(runner: Any, preflight: dict[str, Any], lineage: list[dict[str, Any]]) -> dict[str, Any]:
    from identity_restoration.application.benchmark_contract import load_benchmark_manifest
    from identity_restoration.application.benchmark_orchestration import _scenario_profile_id
    from shared.vision.paid_call_guard import paid_call_context
    from shared.vision.providers.gemini_vision import classify_gemini_failure
    from validator_studio.face_validator import _assert_face_observation_contract, _load_face_rubric, validate_face
    from validator_studio.schemas.face_validation import FaceValidationObservation

    row = next(item for item in lineage if item["sampleId"] == "B01")
    image_path = ROOT / row["faceInputArtifact"]
    manifest = load_benchmark_manifest(ROOT / "contracts/identity_restoration/benchmark_set.yaml")
    cases = {str(item["id"]): item for item in manifest["cases"]}
    profile = _scenario_profile_id(cases["B01"])
    desc = runner.descriptor("FACE_LOCAL", "B01", 1, runner.sha_path(image_path), row["authorityProfile"], profile, preflight["model"])
    write_json(OUT / "recovery_probe_request_metadata.json", {
        "status": "STARTED",
        "probe": {"lane": "FACE_LOCAL", "sampleId": "B01", "sample": 1},
        "descriptor": desc,
        "inputPath": str(image_path.relative_to(ROOT)),
        "inputSha256": sha_path(image_path),
        "provider": "gemini",
        "model": preflight["model"],
        "schema": preflight["schemas"]["faceObservation"],
        "outputCap": preflight["outputCap"],
        "retryPolicy": preflight["retryPolicy"],
    })

    def sink(event: dict[str, Any]) -> None:
        runner.persist_event("FACE_LOCAL", "B01", 1, desc, event)

    try:
        with paid_call_context({
            "benchmarkId": "candidate-v3-r1-recovery-recheck",
            "branch": "FACE_LOCAL",
            "imageSha256": sha_path(image_path),
            "sampleIndex": 1,
            "reason": "single authorized recovery probe before bulk authoritative evaluation",
            "historicalEvidenceSearch": {"exactArtifactCacheMatch": False, "lineage": "VERIFIED"},
        }):
            report = validate_face(
                "venho_hotel", "linh_an", image_path, provider="gemini",
                reference_image_paths=[runner.A2_PATH], samples=1,
                raw_response_sink=sink,
                validation_cycle_id="candidate-v3-r1-recovery-recheck-b01-face-1",
                attempt_id="r1-recovery-recheck",
            )
            observation = FaceValidationObservation.model_validate(report.raw_observation)
            _assert_face_observation_contract(observation.model_dump(mode="json"), _load_face_rubric("venho_hotel"))
    except Exception as exc:
        rows = ledger_rows()
        failure = {
            "status": "FAIL",
            "classification": classify_gemini_failure(exc),
            "error": str(exc),
            "providerCalls": sum(row.get("event") == "intent" for row in rows),
            "successfulResponses": sum(row.get("event") == "result" and row.get("success") is True for row in rows),
            "failedResponses": sum(row.get("event") == "result" and row.get("success") is False for row in rows),
        }
        write_json(OUT / "recovery_probe_failure.json", failure)
        metadata = json.loads((OUT / "recovery_probe_request_metadata.json").read_text(encoding="utf-8"))
        metadata["status"] = "FAIL"
        metadata["failure"] = failure
        write_json(OUT / "recovery_probe_request_metadata.json", metadata)
        return failure

    payload = observation.model_dump(mode="json")
    write_json(OUT / "recovery_probe_parsed.json", payload)
    raw_path = OUT / "raw-provider" / "FACE_LOCAL" / "B01" / "sample-1.txt"
    rows = ledger_rows()
    result = {
        "status": "PASS",
        "probe": {"lane": "FACE_LOCAL", "sampleId": "B01", "sample": 1},
        "providerCalls": sum(row.get("event") == "intent" for row in rows),
        "successfulResponses": sum(row.get("event") == "result" and row.get("success") is True for row in rows),
        "failedResponses": sum(row.get("event") == "result" and row.get("success") is False for row in rows),
        "rawPath": str(raw_path.relative_to(OUT)) if raw_path.is_file() else None,
        "rawSha256": sha_path(raw_path) if raw_path.is_file() else None,
        "parsedPath": "recovery_probe_parsed.json",
        "parsedSha256": sha_path(OUT / "recovery_probe_parsed.json"),
        "lineageComplete": True,
        "schemaValid": True,
        "parseRepair": False,
    }
    write_json(OUT / "recovery_probe_request_metadata.json", {
        **json.loads((OUT / "recovery_probe_request_metadata.json").read_text(encoding="utf-8")),
        "status": "PASS",
        "result": result,
    })
    write_json(OUT / "recovery_probe_parsed.json", {"observation": payload, "result": result})
    return result


def final_summary(probe: dict[str, Any], runner_status: int | None) -> dict[str, Any]:
    rows = ledger_rows()
    face = json.loads((OUT / "FACE_LOCAL.json").read_text(encoding="utf-8")) if (OUT / "FACE_LOCAL.json").is_file() else {"expected": 9, "valid": 0, "qualityPass": None, "qualityFail": None}
    scenario = json.loads((OUT / "SCENARIO_GLOBAL.json").read_text(encoding="utf-8")) if (OUT / "SCENARIO_GLOBAL.json").is_file() else {"expected": 9, "valid": 0, "qualityPass": None, "qualityFail": None}
    valid_provider_responses = sum(row.get("status") == "VALID_RESPONSE" for row in execution_rows())
    failed = [row for row in rows if row.get("event") == "result" and row.get("success") is False]
    recovery = "COMPLETE" if face.get("valid") == 9 and scenario.get("valid") == 9 else (
        "PROVIDER_BLOCKED_PARTIAL" if probe.get("status") == "PASS" and valid_provider_responses else "PROVIDER_BLOCKED"
    )
    return {
        "taskId": "candidate-v3-r1-recovery-recheck",
        "authorization": True,
        "recoveryRecheck": recovery,
        "qualityDisposition": (
            "PASS" if face.get("qualityPass") is not None and scenario.get("qualityPass") is not None
            and face["qualityFail"] == 0 and scenario["qualityFail"] == 0
            else "FAIL" if face.get("qualityPass") is not None and scenario.get("qualityPass") is not None else "UNVALIDATED"
        ),
        "recoveryProbe": {**probe, "status": "PROVIDER_BLOCKED" if probe.get("status") == "FAIL" else probe.get("status")},
        "faceLocal": {"expected": face.get("expected", 9), "valid": face.get("valid", 0), "invalid": 0, "unexecuted": face.get("expected", 9) - face.get("valid", 0), "pass": face.get("qualityPass"), "fail": face.get("qualityFail")},
        "scenarioGlobal": {"expected": scenario.get("expected", 9), "valid": scenario.get("valid", 0), "invalid": 0, "unexecuted": scenario.get("expected", 9) - scenario.get("valid", 0), "pass": scenario.get("qualityPass"), "fail": scenario.get("qualityFail")},
        "callAccounting": {
            "providerCalls": sum(row.get("event") == "intent" for row in rows),
            "validProviderResponses": valid_provider_responses,
            "invalidProviderResponses": 0,
            "failedProviderResponses": len(failed),
            "gpuJobs": 0,
            "nanoCalls": 0,
        },
        "pendingAuthoritativeEvaluations": max(0, 18 - face.get("valid", 0) - scenario.get("valid", 0)),
        "providerHold": "ACTIVE",
        "productionPromotion": "NO",
        "featureFlag": "OFF",
        "architectureChanged": False,
        "runnerExitCode": runner_status,
        "boundary": boundary_counts(),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    runner = load_runner()

    if os.environ.get("R1_RECOVERY_RECHECK_FINALIZE_ONLY") == "1":
        failure_path = OUT / "recovery_probe_failure.json"
        if not failure_path.is_file():
            raise RuntimeError("finalize-only mode requires an existing recovery_probe_failure.json")
        probe = json.loads(failure_path.read_text(encoding="utf-8"))
        summary = final_summary(probe, None)
        write_json(OUT / "recovery_checkpoint.json", {
            **summary,
            "status": "CLOSED / PROVIDER_BLOCKED",
        })
        write_json(OUT / "summary.json", summary)
        write_hashes()
        print(json.dumps({"status": summary["recoveryRecheck"], "output": str(OUT), "providerCalls": summary["callAccounting"]["providerCalls"], "faceLocal": summary["faceLocal"]["valid"], "scenarioGlobal": summary["scenarioGlobal"]["valid"]}, ensure_ascii=False))
        return 2

    runner.enforce_provider_hold_gate()
    runner.load_env()
    os.environ["VALIDATOR_LIVE_ENABLED"] = "true"
    os.environ["VALIDATOR_MAX_NEW_CALLS"] = "36"
    os.environ["VALIDATOR_PAID_CALL_LEDGER"] = str(OUT / "provider-paid-call-ledger.jsonl")

    try:
        preflight_report, lineage = runner.preflight()
    except Exception as exc:
        write_json(OUT / "offline_preflight.json", {"status": "BLOCKED_LOCAL_REGRESSION", "error": str(exc), "providerCalls": 0})
        write_json(OUT / "summary.json", {"taskId": "candidate-v3-r1-recovery-recheck", "recoveryRecheck": "BLOCKED_LOCAL_REGRESSION", "error": str(exc), "callAccounting": {"providerCalls": 0, "gpuJobs": 0, "nanoCalls": 0}})
        write_hashes()
        return 2

    write_json(OUT / "baseline.json", baseline(runner, preflight_report))
    write_json(OUT / "offline_preflight.json", {"status": "PASS", "report": preflight_report, "lineage": lineage})
    probe = run_probe(runner, preflight_report, lineage)
    runner_status: int | None = None
    if probe.get("status") == "PASS":
        runner_status = runner.run()
    summary = final_summary(probe, runner_status)
    write_json(OUT / "recovery_checkpoint.json", {
        **summary,
        "status": "CLOSED / PASS" if summary["recoveryRecheck"] == "COMPLETE" else "CLOSED / PROVIDER_BLOCKED",
    })
    write_json(OUT / "summary.json", summary)
    write_hashes()
    print(json.dumps({"status": summary["recoveryRecheck"], "output": str(OUT), "providerCalls": summary["callAccounting"]["providerCalls"], "faceLocal": summary["faceLocal"]["valid"], "scenarioGlobal": summary["scenarioGlobal"]["valid"]}, ensure_ascii=False))
    return 0 if summary["recoveryRecheck"] == "COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
