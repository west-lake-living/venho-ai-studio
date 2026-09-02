#!/usr/bin/env python3
"""Run the single explicitly authorized Candidate v3 R1-P5-R4 recheck."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PHASE7 = ROOT / "artifacts/identity-restoration/phase7-candidate-v3"
HOLD = PHASE7 / "r1-p4-r3-provider-hold-active.json"
INNER = ROOT / "scripts/run_candidate_v3_r1_p5_r3_provider_recovery_recheck.py"
OUT = Path(os.environ.get(
    "R1_P5_R4_OUTPUT_DIR",
    str(PHASE7 / ("r1-p5-r4-provider-recovery-recheck-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))),
))
TASK_ID = "R1-P5-R4-PROVIDER-RECOVERY-RECHECK"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def start_state() -> dict[str, Any]:
    hold = json.loads(HOLD.read_text(encoding="utf-8"))
    if hold["provider_hold"]["active"] is not True:
        raise RuntimeError("PROVIDER_HOLD_NOT_ACTIVE")
    return {
        "r1P5": "CLOSED / PASS",
        "r1P5R1": "CLOSED / PROVIDER_BLOCKED",
        "r1P5R2": "CLOSED / PROVIDER_BLOCKED",
        "r1P5R3": "CLOSED / PROVIDER_BLOCKED",
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


def auth_payload() -> dict[str, Any]:
    return {
        "name": "PROVIDER_RECOVERY_RECHECK_AUTHORIZED",
        "requiredValue": "TRUE",
        "receivedValue": os.environ.get("PROVIDER_RECOVERY_RECHECK_AUTHORIZED"),
    }


def run_offline(command: list[str]) -> tuple[int, str]:
    clean_env = dict(os.environ)
    clean_env.pop("VALIDATOR_LIVE_ENABLED", None)
    clean_env.pop("GEMINI_API_KEY", None)
    clean_env.pop("GOOGLE_API_KEY", None)
    result = subprocess.run(command, cwd=ROOT, env=clean_env, text=True, capture_output=True, check=False)
    return result.returncode, (result.stdout + result.stderr).rstrip() + "\n"


def write_hashes() -> None:
    files = {
        str(path.relative_to(OUT)): sha256(path)
        for path in sorted(OUT.rglob("*"))
        if path.is_file() and path.name != "hashes.sha256"
    }
    write_json(OUT / "hashes.sha256", {"algorithm": "SHA-256", "files": files, "count": len(files)})


def rewrite_identity() -> None:
    for filename in ("baseline.json", "probe_request_metadata.json", "summary.json"):
        path = OUT / filename
        if not path.is_file():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["taskId"] = TASK_ID
        payload["authorization"] = auth_payload()
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
            payload["attemptId"] = "r1-p5-r4-b01-face-1"
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
                record["benchmarkId"] = "candidate-v3-r1-p5-r4-provider-recovery-recheck"
            else:
                record["attemptId"] = "r1-p5-r4"
                record["cycleId"] = "candidate-v3-r1-p5-r4-b01-face-1"
            records.append(json.dumps(record, ensure_ascii=False, sort_keys=True))
        path.write_text("\n".join(records) + "\n", encoding="utf-8")


def ensure_provider_error() -> None:
    metadata_path = OUT / "probe_request_metadata.json"
    summary_path = OUT / "summary.json"
    if not metadata_path.is_file() or not summary_path.is_file():
        return
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    classification = metadata.get("classification") or summary.get("blocker")
    if summary.get("status") != "PASS" and classification:
        write_json(OUT / "provider_error.json", {
            "taskId": TASK_ID,
            "provider": summary.get("provider", "Gemini"),
            "model": summary.get("model", "gemini-flash-latest"),
            "classification": classification,
            "providerCalls": summary.get("providerCalls", 0),
            "retries": summary.get("retries", 0),
            "responseReturned": metadata.get("rawSha256") is not None,
            "rawResponseCaptured": metadata.get("rawSha256") is not None,
            "parsedResponseCaptured": metadata.get("parsedSha256") is not None,
        })


def finalize_timeout_evidence() -> int:
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
        "attemptId": "r1-p5-r4-b01-face-1",
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
    rewrite_identity()
    ensure_provider_error()
    restore_preflight_artifacts()
    write_hashes()
    return 2


def restore_preflight_artifacts() -> None:
    for name in ("offline_preflight.json", "test_results.txt", "compileall.txt", "git_diff_check.txt"):
        snapshot = OUT / ("r4_" + name)
        if snapshot.is_file():
            target = OUT / name
            if target.suffix == ".json":
                target.write_text(snapshot.read_text(encoding="utf-8"), encoding="utf-8")
            else:
                target.write_text(snapshot.read_text(encoding="utf-8"), encoding="utf-8")


def main() -> int:
    state = start_state()
    OUT.mkdir(parents=True, exist_ok=True)
    if os.environ.get("R1_P5_R4_FINALIZE_TIMEOUT") == "1":
        return finalize_timeout_evidence()

    write_json(OUT / "r4_authorization_and_start_state.json", {
        "taskId": TASK_ID,
        "authorization": auth_payload(),
        "startState": state,
        "limits": {"maxProviderCalls": 1, "maxRetries": 0, "bulkEvaluationsAuthorized": False},
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

    focused_tests = [
        "tests/test_candidate_v3_r1_p4_r3_provider_hold.py",
        "tests/test_candidate_v3_r1_p5_provider_recovery_gate.py",
        "tests/test_candidate_v3_p5_r1_provider_recovery_probe.py",
        "tests/test_candidate_v3_p5_r2_provider_recovery_recheck.py",
        "tests/test_candidate_v3_p5_r3_provider_recovery_recheck.py",
        "tests/test_candidate_v3_p5_r4_provider_recovery_recheck.py",
        "tests/test_gemini_validator_transport.py",
    ]
    test_code, test_output = run_offline(["python3", "-m", "pytest", "-q", *focused_tests])
    compile_code, compile_output = run_offline(["python3", "-m", "compileall", "-q", "shared/vision/provider_recovery_gate.py", "shared/vision/providers/gemini_vision.py", "scripts/run_candidate_v3_r1_p5_r1_provider_recovery_probe.py", "scripts/run_candidate_v3_r1_p5_r2_provider_recovery_recheck.py", "scripts/run_candidate_v3_r1_p5_r3_provider_recovery_recheck.py", "scripts/run_candidate_v3_r1_p5_r4_provider_recovery_recheck.py"])
    diff_code, diff_output = run_offline(["git", "diff", "--check"])
    preflight = {
        "status": "PASS" if test_code == compile_code == diff_code == 0 else "BLOCKED_LOCAL_REGRESSION",
        "providerCalls": 0,
        "gpuJobs": 0,
        "nanoCalls": 0,
        "credentialLoad": "not_performed",
        "testExitCode": test_code,
        "compileallExitCode": compile_code,
        "gitDiffCheckExitCode": diff_code,
        "approvedProvider": "Gemini",
        "approvedModel": "gemini-flash-latest",
        "transportAttempts": 1,
        "retries": 0,
    }
    write_json(OUT / "offline_preflight.json", preflight)
    (OUT / "test_results.txt").write_text(test_output, encoding="utf-8")
    (OUT / "compileall.txt").write_text(compile_output, encoding="utf-8")
    (OUT / "git_diff_check.txt").write_text(diff_output, encoding="utf-8")
    for name in ("offline_preflight.json", "test_results.txt", "compileall.txt", "git_diff_check.txt"):
        (OUT / ("r4_" + name)).write_text((OUT / name).read_text(encoding="utf-8"), encoding="utf-8")

    if test_code != 0 or compile_code != 0 or diff_code != 0:
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
    env["R1_P5_R3_OUTPUT_DIR"] = str(OUT)
    env["GEMINI_MAX_TRANSPORT_ATTEMPTS"] = "1"
    env["VALIDATOR_MAX_NEW_CALLS"] = "1"
    try:
        result = subprocess.run(
            [sys.executable, str(INNER)], cwd=ROOT, env=env, text=True,
            capture_output=True, check=False, timeout=90,
        )
    except subprocess.TimeoutExpired as exc:
        (OUT / "r1_p5_r3_runner_stdout_stderr.txt").write_text(
            (exc.stdout or "") + (exc.stderr or ""), encoding="utf-8"
        )
        return finalize_timeout_evidence()

    (OUT / "r1_p5_r3_runner_stdout_stderr.txt").write_text(result.stdout + result.stderr, encoding="utf-8")
    rewrite_identity()
    ensure_provider_error()
    restore_preflight_artifacts()
    write_hashes()
    summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
    print(json.dumps({"status": summary.get("status"), "output": str(OUT), "providerCalls": summary.get("providerCalls")}, ensure_ascii=False))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
