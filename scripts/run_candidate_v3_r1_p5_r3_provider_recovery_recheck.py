#!/usr/bin/env python3
"""Run the single explicitly authorized Candidate v3 R1-P5-R3 recheck."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PHASE7 = ROOT / "artifacts/identity-restoration/phase7-candidate-v3"
HOLD = PHASE7 / "r1-p4-r3-provider-hold-active.json"
INNER = ROOT / "scripts/run_candidate_v3_r1_p5_r2_provider_recovery_recheck.py"
OUT = Path(os.environ.get(
    "R1_P5_R3_OUTPUT_DIR",
    str(PHASE7 / ("r1-p5-r3-provider-recovery-recheck-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))),
))
TASK_ID = "R1-P5-R3-PROVIDER-RECOVERY-RECHECK"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def start_state() -> dict[str, Any]:
    hold = json.loads(HOLD.read_text(encoding="utf-8"))
    if hold["provider_hold"]["active"] is not True:
        raise RuntimeError("PROVIDER_HOLD_NOT_ACTIVE")
    return {
        "r1P5": "CLOSED / PASS",
        "r1P5R1": "CLOSED / PROVIDER_BLOCKED",
        "r1P5R2": "CLOSED / PROVIDER_BLOCKED",
        "providerHold": "ACTIVE",
        "provider": hold["provider_hold"]["provider"],
        "model": hold["provider_hold"]["model"],
        "boundary": {"pass": 9, "fail": 0},
        "faceLocal": {"expected": 9, "valid": 0},
        "scenarioGlobal": {"expected": 9, "valid": 0},
        "pendingAuthoritativeEvaluations": 18,
        "qualityDisposition": "UNVALIDATED",
        "featureFlag": "OFF",
        "productionPromotion": "NO",
        "architectureChanged": False,
    }


def rewrite_r3_identity() -> None:
    for filename in ("baseline.json", "probe_request_metadata.json", "summary.json"):
        path = OUT / filename
        if not path.is_file():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["taskId"] = TASK_ID
        payload["authorization"] = {
            "name": "PROVIDER_RECOVERY_RECHECK_AUTHORIZED",
            "requiredValue": "TRUE",
            "receivedValue": os.environ.get("PROVIDER_RECOVERY_RECHECK_AUTHORIZED"),
        }
        if filename == "summary.json":
            recovered = payload.get("status") == "PASS"
            payload.update({
                "taskStatus": "CLOSED / PASS" if recovered else "CLOSED / PROVIDER_BLOCKED",
                "recoveryProbe": "PASS" if recovered else "PROVIDER_BLOCKED",
                "providerRecoveryStatus": "PASS" if recovered else "PROVIDER_BLOCKED",
                "nextAction": (
                    "AUTHORITATIVE_EVALUATION_RESUME_REQUIRES_SEPARATE_AUTHORIZATION"
                    if recovered else "KEEP_PROVIDER_HOLD_ACTIVE"
                ),
                "startState": start_state(),
            })
        elif filename == "probe_request_metadata.json":
            payload["attemptId"] = "r1-p5-r3-b01-face-1"
        write_json(path, payload)

    for filename in ("provider-paid-call-ledger.jsonl", "attempt-history.jsonl"):
        path = OUT / filename
        if not path.is_file():
            continue
        records = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if filename == "provider-paid-call-ledger.jsonl":
                record["benchmarkId"] = "candidate-v3-r1-p5-r3-provider-recovery-recheck"
            else:
                record["attemptId"] = "r1-p5-r3"
                record["cycleId"] = "candidate-v3-r1-p5-r3-b01-face-1"
            records.append(json.dumps(record, ensure_ascii=False, sort_keys=True))
        path.write_text("\n".join(records) + "\n", encoding="utf-8")


def write_hashes() -> None:
    files = {
        str(path.relative_to(OUT)): sha256(path)
        for path in sorted(OUT.rglob("*"))
        if path.is_file() and path.name != "hashes.sha256"
    }
    write_json(OUT / "hashes.sha256", {"algorithm": "SHA-256", "files": files, "count": len(files)})


def finalize_timeout_evidence() -> int:
    """Finalize an interrupted single call without making another call."""
    intent_path = OUT / "provider-paid-call-ledger.jsonl"
    provider_calls = sum(
        1 for line in intent_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and json.loads(line).get("event") == "intent"
    ) if intent_path.is_file() else 0
    if provider_calls != 1:
        raise RuntimeError(f"EXPECTED_ONE_PROVIDER_INTENT:{provider_calls}")
    metadata_path = OUT / "probe_request_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata.update({
        "taskId": TASK_ID,
        "attemptId": "r1-p5-r3-b01-face-1",
        "status": "PROVIDER_BLOCKED",
        "providerCalls": 1,
        "successfulResponses": 0,
        "failedResponses": 1,
        "classification": "PROVIDER_TIMEOUT",
        "rawSha256": None,
        "parsedSha256": None,
        "gateAssessment": {
            "passed": False,
            "failedCriteria": [
                "request_succeeded", "no_timeout", "parsed_without_repair",
                "required_fields_present", "dto_schema_valid",
                "raw_response_preserved", "raw_response_hash_recorded",
                "authoritative_response",
            ],
            "qualityVerdict": None,
        },
    })
    write_json(metadata_path, metadata)
    write_json(OUT / "probe_completion.json", {
        "taskId": TASK_ID,
        "status": "PROVIDER_BLOCKED",
        "classification": "PROVIDER_TIMEOUT",
        "providerCalls": 1,
        "retries": 0,
        "responseReturned": False,
        "rawResponseCaptured": False,
        "parsedResponseCaptured": False,
        "observation": "The single authorized runner process ended while waiting for the provider response; no response or retry was recorded.",
    })
    write_json(OUT / "summary.json", {
        "taskId": TASK_ID,
        "taskStatus": "CLOSED / PROVIDER_BLOCKED",
        "status": "PROVIDER_BLOCKED",
        "recoveryProbe": "PROVIDER_BLOCKED",
        "providerRecoveryStatus": "PROVIDER_BLOCKED",
        "providerHold": "ACTIVE",
        "provider": "Gemini",
        "model": "gemini-flash-latest",
        "providerCalls": 1,
        "successfulResponses": 0,
        "failedResponses": 1,
        "retries": 0,
        "transportAttempts": 1,
        "blocker": "PROVIDER_TIMEOUT",
        "validResponse": False,
        "rawHash": None,
        "parsedHash": None,
        "gpuJobs": 0,
        "nanoCalls": 0,
        "alternativeProviderCalls": 0,
        "boundary": {"pass": 9, "fail": 0},
        "faceLocal": {"expected": 9, "valid": 0},
        "scenarioGlobal": {"expected": 9, "valid": 0},
        "pendingAuthoritativeEvaluations": 18,
        "qualityDisposition": "UNVALIDATED",
        "featureFlag": "OFF",
        "productionPromotion": "NO",
        "architectureChanged": False,
        "nextAction": "KEEP_PROVIDER_HOLD_ACTIVE",
        "startState": start_state(),
    })
    rewrite_r3_identity()
    write_hashes()
    return 2


def main() -> int:
    state = start_state()
    OUT.mkdir(parents=True, exist_ok=True)
    if os.environ.get("R1_P5_R3_FINALIZE_TIMEOUT") == "1":
        return finalize_timeout_evidence()
    write_json(OUT / "r3_authorization_and_start_state.json", {
        "taskId": TASK_ID,
        "authorization": {
            "name": "PROVIDER_RECOVERY_RECHECK_AUTHORIZED",
            "requiredValue": "TRUE",
            "receivedValue": os.environ.get("PROVIDER_RECOVERY_RECHECK_AUTHORIZED"),
        },
        "startState": state,
        "limits": {
            "maxProviderCalls": 1,
            "maxRetries": 0,
            "bulkEvaluationsAuthorized": False,
        },
    })
    if not INNER.is_file():
        write_json(OUT / "summary.json", {
            "taskId": TASK_ID,
            "taskStatus": "BLOCKED_LOCAL_REGRESSION",
            "status": "BLOCKED_LOCAL_REGRESSION",
            "providerCalls": 0,
            "providerHold": "ACTIVE",
        })
        write_hashes()
        return 2

    env = dict(os.environ)
    env["R1_P5_R2_OUTPUT_DIR"] = str(OUT)
    env["GEMINI_MAX_TRANSPORT_ATTEMPTS"] = "1"
    env["VALIDATOR_MAX_NEW_CALLS"] = "1"
    result = subprocess.run(
        [sys.executable, str(INNER)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    (OUT / "r1_p5_r2_runner_stdout_stderr.txt").write_text(
        result.stdout + result.stderr, encoding="utf-8"
    )
    rewrite_r3_identity()
    write_hashes()
    summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
    print(json.dumps({
        "status": summary.get("status"),
        "output": str(OUT),
        "providerCalls": summary.get("providerCalls"),
    }, ensure_ascii=False))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
