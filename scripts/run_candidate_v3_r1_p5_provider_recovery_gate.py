#!/usr/bin/env python3
"""Record the offline R1-P5 provider recovery-gate decision.

R1-P5 is a control-plane task.  This harness never loads credentials, enables
live validation, or invokes a provider.  A later task must separately
authorize and execute a minimal probe after this gate is in place.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shared.vision.provider_recovery_gate import (
    AUTHORIZATION_ENV,
    APPROVED_MODEL,
    APPROVED_PROVIDER,
    MAX_RECOVERY_PROBES,
    ProviderRecoveryBlocked,
    ProviderRecoveryGate,
)


ROOT = Path(__file__).resolve().parents[1]
PHASE7 = ROOT / "artifacts/identity-restoration/phase7-candidate-v3"
HOLD_GATE = PHASE7 / "r1-p4-r3-provider-hold-active.json"
P1 = PHASE7 / "r1-p1-boundary-remediation-20260828"
OUT = Path(os.environ.get(
    "R1_P5_OUTPUT_DIR",
    str(PHASE7 / ("r1-p5-provider-recovery-gate-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))),
))


def sha_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def boundary_counts() -> dict[str, int]:
    rows = json.loads((P1 / "per-sample-results.json").read_text(encoding="utf-8"))["samples"]
    return {
        "pass": sum(row["postRemediation"]["status"] == "PASS" for row in rows),
        "fail": sum(row["postRemediation"]["status"] != "PASS" for row in rows),
    }


def run_offline(command: list[str]) -> tuple[int, str]:
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    output = (completed.stdout + completed.stderr).rstrip() + "\n"
    return completed.returncode, output


def write_hashes() -> None:
    files = {
        str(path.relative_to(OUT)): sha_path(path)
        for path in sorted(OUT.rglob("*"))
        if path.is_file() and path.name != "hashes.sha256"
    }
    write_json(OUT / "hashes.sha256", {"algorithm": "SHA-256", "files": files, "count": len(files)})


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    hold = json.loads(HOLD_GATE.read_text(encoding="utf-8"))
    boundary = boundary_counts()
    environment = dict(os.environ)
    gate = ProviderRecoveryGate(hold, environment=environment)

    write_json(OUT / "baseline.json", {
        "taskId": "candidate-v3-r1-p5-provider-recovery-gate",
        "capturedAt": datetime.now(timezone.utc).isoformat(),
        "providerHold": hold["provider_hold"],
        "boundary": boundary,
        "faceLocal": {"expected": 9, "valid": 0, "disposition": "UNVALIDATED / PROVIDER_BLOCKED"},
        "scenarioGlobal": {"expected": 9, "valid": 0, "disposition": "UNVALIDATED / PROVIDER_BLOCKED"},
        "pendingAuthoritativeEvaluations": 18,
        "qualityDisposition": "UNVALIDATED",
        "featureFlag": "OFF",
        "productionPromotion": "NO",
    })
    write_json(OUT / "gate_policy.json", {
        "schemaVersion": "candidate-v3-r1-p5-provider-recovery-gate-1.0",
        "states": [state.value for state in gate.state.__class__],
        "approvedProvider": APPROVED_PROVIDER,
        "approvedModel": APPROVED_MODEL,
        "maxRecoveryProbeCalls": MAX_RECOVERY_PROBES,
        "bulkEvaluationInR1P5": "BLOCKED",
        "pendingEvaluationsPreserved": 18,
        "automaticFallback": False,
        "automaticModelSwitch": False,
        "nanoCalls": 0,
        "gpuJobs": 0,
    })
    write_json(OUT / "authorization_policy.json", {
        "name": AUTHORIZATION_ENV,
        "acceptedValue": "TRUE",
        "rawValuePresent": environment.get(AUTHORIZATION_ENV) is not None,
        "rawValue": environment.get(AUTHORIZATION_ENV),
        "malformedOrUnknownValuesRemainActive": True,
        "authorizationInferred": False,
        "defaultProviderCalls": 0,
    })

    try:
        gate.authorize_recovery()
        authorization_result = "RECOVERY_CHECK_AUTHORIZED"
    except ProviderRecoveryBlocked as exc:
        authorization_result = "ACTIVE"
        authorization_error = str(exc)
    else:
        authorization_error = None

    compile_code, compile_output = run_offline(["python3", "-m", "compileall", "-q", "shared/vision/provider_recovery_gate.py", "scripts/run_candidate_v3_r1_p5_provider_recovery_gate.py"])
    diff_code, diff_output = run_offline(["git", "diff", "--check"])
    tests_code, tests_output = run_offline([
        "python3", "-m", "pytest", "-q", "tests/test_candidate_v3_r1_p5_provider_recovery_gate.py",
    ])
    (OUT / "compileall.txt").write_text(compile_output, encoding="utf-8")
    (OUT / "git_diff_check.txt").write_text(diff_output, encoding="utf-8")
    (OUT / "test_results.txt").write_text(tests_output, encoding="utf-8")
    write_json(OUT / "offline_preflight.json", {
        "status": "PASS" if compile_code == diff_code == tests_code == 0 else "BLOCKED_LOCAL_REGRESSION",
        "providerCalls": 0,
        "gpuJobs": 0,
        "nanoCalls": 0,
        "credentialLoad": "not_performed",
        "liveValidation": "not_enabled",
        "compileallExitCode": compile_code,
        "gitDiffCheckExitCode": diff_code,
        "testsExitCode": tests_code,
    })
    write_json(OUT / "summary.json", {
        "taskId": "candidate-v3-r1-p5-provider-recovery-gate",
        "status": "CLOSED / PASS" if compile_code == diff_code == tests_code == 0 else "BLOCKED_LOCAL_REGRESSION",
        "providerHold": gate.state.value,
        "authorizationResult": authorization_result,
        "authorizationError": authorization_error,
        "probeStarted": False,
        "providerCalls": 0,
        "maxRecoveryProbeCalls": MAX_RECOVERY_PROBES,
        "faceLocal": {"expected": 9, "valid": 0, "pending": 9},
        "scenarioGlobal": {"expected": 9, "valid": 0, "pending": 9},
        "pendingAuthoritativeEvaluations": 18,
        "boundary": boundary,
        "qualityDisposition": "UNVALIDATED",
        "featureFlag": "OFF",
        "productionPromotion": "NO",
        "automaticFallbackCalls": 0,
        "automaticModelSwitches": 0,
        "nanoCalls": 0,
        "gpuJobs": 0,
        "stateSnapshot": gate.snapshot(),
    })
    write_json(OUT / "recovery_checkpoint.json", {
        "status": "HOLD_REMAINS_ACTIVE",
        "provider": APPROVED_PROVIDER,
        "model": APPROVED_MODEL,
        "providerCalls": 0,
        "transitions": list(gate.transitions),
        "nextAction": "NEW_EXPLICIT_AUTHORIZATION_REQUIRED_FOR_MINIMAL_PROBE",
    })
    write_hashes()
    print(json.dumps({"status": "PASS" if compile_code == diff_code == tests_code == 0 else "BLOCKED_LOCAL_REGRESSION", "output": str(OUT), "providerCalls": 0}, ensure_ascii=False))
    return 0 if compile_code == diff_code == tests_code == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
