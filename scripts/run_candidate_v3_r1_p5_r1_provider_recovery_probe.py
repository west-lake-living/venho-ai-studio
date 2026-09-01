#!/usr/bin/env python3
"""Execute the single explicitly authorized Candidate v3 recovery probe."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shared.vision.paid_call_guard import paid_call_context
from shared.vision.provider_recovery_gate import (
    APPROVED_MODEL,
    APPROVED_PROVIDER,
    AUTHORIZATION_ENV,
    ProviderRecoveryBlocked,
    ProviderRecoveryGate,
)


ROOT = Path(__file__).resolve().parents[1]
PHASE7 = ROOT / "artifacts/identity-restoration/phase7-candidate-v3"
HOLD_GATE = PHASE7 / "r1-p4-r3-provider-hold-active.json"
P1 = PHASE7 / "r1-p1-boundary-remediation-20260828"
RUNNER_PATH = ROOT / "scripts/run_candidate_v3_r1_p4_r1_provider_remediation.py"
OUT = Path(os.environ.get(
    "R1_P5_R1_OUTPUT_DIR",
    str(PHASE7 / ("r1-p5-r1-provider-recovery-probe-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))),
))


def sha_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def load_runner() -> Any:
    os.environ["R1_P4_R1_OUTPUT_DIR"] = str(OUT)
    spec = importlib.util.spec_from_file_location("candidate_v3_r1_p4_runner_probe", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load existing authoritative runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def boundary_counts() -> dict[str, int]:
    rows = json.loads((P1 / "per-sample-results.json").read_text(encoding="utf-8"))["samples"]
    return {"pass": sum(row["postRemediation"]["status"] == "PASS" for row in rows), "fail": sum(row["postRemediation"]["status"] != "PASS" for row in rows)}


def ledger_rows() -> list[dict[str, Any]]:
    path = OUT / "provider-paid-call-ledger.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def run_offline(command: list[str]) -> tuple[int, str]:
    clean_env = dict(os.environ)
    clean_env.pop("VALIDATOR_LIVE_ENABLED", None)
    clean_env.pop("GEMINI_API_KEY", None)
    clean_env.pop("GOOGLE_API_KEY", None)
    result = subprocess.run(command, cwd=ROOT, env=clean_env, text=True, capture_output=True, check=False)
    return result.returncode, (result.stdout + result.stderr).rstrip() + "\n"


def write_hashes() -> None:
    files = {str(path.relative_to(OUT)): sha_path(path) for path in sorted(OUT.rglob("*")) if path.is_file() and path.name != "hashes.sha256"}
    write_json(OUT / "hashes.sha256", {"algorithm": "SHA-256", "files": files, "count": len(files)})


def finalize_existing_evidence(source: Path) -> int:
    """Create a corrected immutable copy without another provider call."""
    source = source if source.is_absolute() else ROOT / source
    source = source.resolve()
    if not source.is_dir() or not (source / "summary.json").is_file():
        raise RuntimeError(f"cannot finalize missing probe evidence: {source}")
    shutil.copytree(source, OUT, dirs_exist_ok=True)
    summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
    if summary.get("status") == "PROVIDER_BLOCKED":
        summary["nextAction"] = "KEEP_PROVIDER_HOLD_ACTIVE"
    summary["finalizedFrom"] = str(source.relative_to(ROOT))
    write_json(OUT / "summary.json", summary)
    write_hashes()
    print(json.dumps({"status": summary.get("status"), "output": str(OUT), "providerCalls": summary.get("providerCalls", 0), "providerHold": summary.get("providerHold")}, ensure_ascii=False))
    return 0 if summary.get("status") == "PASS" else 2


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    source = os.environ.get("R1_P5_R1_FINALIZE_FROM")
    if source:
        return finalize_existing_evidence(Path(source))
    hold = json.loads(HOLD_GATE.read_text(encoding="utf-8"))
    gate = ProviderRecoveryGate(hold, environment=os.environ)
    boundary = boundary_counts()
    write_json(OUT / "baseline.json", {
        "taskId": "candidate-v3-r1-p5-r1-provider-recovery-probe",
        "authorization": {"name": AUTHORIZATION_ENV, "requiredValue": "TRUE", "receivedValue": os.environ.get(AUTHORIZATION_ENV)},
        "providerHold": "ACTIVE",
        "provider": APPROVED_PROVIDER,
        "model": APPROVED_MODEL,
        "boundary": boundary,
        "faceLocal": {"expected": 9, "valid": 0},
        "scenarioGlobal": {"expected": 9, "valid": 0},
        "pendingAuthoritativeEvaluations": 18,
        "featureFlag": "OFF",
        "productionPromotion": "NO",
        "architectureChanged": False,
    })

    test_code, test_output = run_offline(["python3", "-m", "pytest", "-q", "tests/test_candidate_v3_r1_p5_provider_recovery_gate.py", "tests/test_candidate_v3_p5_r1_provider_recovery_probe.py", "tests/test_gemini_validator_transport.py"])
    compile_code, compile_output = run_offline(["python3", "-m", "compileall", "-q", "shared/vision/provider_recovery_gate.py", "shared/vision/providers/gemini_vision.py", "scripts/run_candidate_v3_r1_p5_r1_provider_recovery_probe.py"])
    diff_code, diff_output = run_offline(["git", "diff", "--check"])
    (OUT / "test_results.txt").write_text(test_output, encoding="utf-8")
    (OUT / "compileall.txt").write_text(compile_output, encoding="utf-8")
    (OUT / "git_diff_check.txt").write_text(diff_output, encoding="utf-8")
    write_json(OUT / "offline_preflight.json", {
        "status": "PASS" if test_code == compile_code == diff_code == 0 else "BLOCKED_LOCAL_REGRESSION",
        "providerCalls": 0,
        "gpuJobs": 0,
        "nanoCalls": 0,
        "credentialLoad": "not_performed",
        "testExitCode": test_code,
        "compileallExitCode": compile_code,
        "gitDiffCheckExitCode": diff_code,
        "approvedProvider": APPROVED_PROVIDER,
        "approvedModel": APPROVED_MODEL,
        "transportAttempts": 1,
        "retries": 0,
    })
    if test_code != 0 or compile_code != 0 or diff_code != 0:
        write_json(OUT / "summary.json", {"taskId": "candidate-v3-r1-p5-r1-provider-recovery-probe", "status": "BLOCKED_LOCAL_REGRESSION", "providerCalls": 0, "providerHold": "ACTIVE"})
        write_hashes()
        return 2

    try:
        gate.begin_recovery_probe()
    except ProviderRecoveryBlocked as exc:
        write_json(OUT / "summary.json", {"taskId": "candidate-v3-r1-p5-r1-provider-recovery-probe", "status": "BLOCKED_AUTHORIZATION", "error": str(exc), "providerCalls": 0, "providerHold": "ACTIVE"})
        write_hashes()
        return 2

    runner = load_runner()
    runner.load_env()
    os.environ["VALIDATOR_LIVE_ENABLED"] = "true"
    os.environ["VALIDATOR_MAX_NEW_CALLS"] = "1"
    os.environ["GEMINI_MAX_TRANSPORT_ATTEMPTS"] = "1"
    os.environ["VALIDATOR_PAID_CALL_LEDGER"] = str(OUT / "provider-paid-call-ledger.jsonl")
    preflight, lineage = runner.preflight()
    row = next(item for item in lineage if item["sampleId"] == "B01")
    image_path = ROOT / row["faceInputArtifact"]
    desc = runner.descriptor("FACE_LOCAL", "B01", 1, runner.sha_path(image_path), row["authorityProfile"], "canonical_default", preflight["model"])
    write_json(OUT / "probe_request_metadata.json", {
        "status": "STARTED",
        "taskId": "R1-P5-R1-PROVIDER-RECOVERY-PROBE",
        "probe": {"lane": "FACE_LOCAL", "sampleId": "B01", "sample": 1},
        "fixture": {"path": str(image_path.relative_to(ROOT)), "sha256": sha_path(image_path), "authority": row["authorityProfile"]},
        "provider": APPROVED_PROVIDER,
        "model": preflight["model"],
        "schema": preflight["schemas"]["faceObservation"],
        "transportAttempts": 1,
        "retries": 0,
        "outputCap": preflight["outputCap"],
        "lineage": "VERIFIED",
    })

    from identity_restoration.application.benchmark_orchestration import _scenario_profile_id
    from shared.vision.providers.gemini_vision import classify_gemini_failure
    from validator_studio.face_validator import _assert_face_observation_contract, _load_face_rubric, validate_face
    from validator_studio.schemas.face_validation import FaceValidationObservation

    captured_raw: str | None = None
    parsed: dict[str, Any] | None = None

    def sink(event: dict[str, Any]) -> None:
        nonlocal captured_raw, parsed
        runner.persist_event("FACE_LOCAL", "B01", 1, desc, event)
        if event.get("rawResponse") is not None:
            captured_raw = str(event["rawResponse"]).rstrip("\n")
            (OUT / "probe_raw.txt").write_text(captured_raw + "\n", encoding="utf-8")
        if event.get("parsedEvidence") is not None:
            parsed = dict(event["parsedEvidence"])
            write_json(OUT / "probe_parsed.json", parsed)

    try:
        with paid_call_context({
            "benchmarkId": "candidate-v3-r1-p5-r1-provider-recovery-probe",
            "branch": "FACE_LOCAL",
            "imageSha256": sha_path(image_path),
            "sampleIndex": 1,
            "reason": "single authorized provider recovery probe",
            "historicalEvidenceSearch": {"exactArtifactCacheMatch": False, "lineage": "VERIFIED"},
        }):
            report = validate_face("venho_hotel", "linh_an", image_path, provider="gemini", reference_image_paths=[runner.A2_PATH], samples=1, raw_response_sink=sink, validation_cycle_id="candidate-v3-r1-p5-r1-b01-face-1", attempt_id="r1-p5-r1")
            observation = FaceValidationObservation.model_validate(report.raw_observation)
            _assert_face_observation_contract(observation.model_dump(mode="json"), _load_face_rubric("venho_hotel"))
        classification = None
        quality_verdict = report.verdict
    except Exception as exc:
        classification = classify_gemini_failure(exc)
        quality_verdict = None

    rows = ledger_rows()
    provider_calls = sum(row.get("event") == "intent" for row in rows)
    successful = sum(row.get("event") == "result" and row.get("success") is True for row in rows)
    failed = sum(row.get("event") == "result" and row.get("success") is False for row in rows)
    evidence = {
        "request_succeeded": classification is None,
        "no_503": classification != "PROVIDER_503",
        "no_timeout": classification != "PROVIDER_TIMEOUT",
        "no_truncation": classification != "PROVIDER_TRUNCATED_RESPONSE",
        "no_malformed_json": classification != "MALFORMED_JSON",
        "no_unsupported_schema": classification != "LOCAL_SCHEMA_BUILD_FAIL",
        "parsed_without_repair": classification is None and parsed is not None,
        "required_fields_present": parsed is not None,
        "dto_schema_valid": classification is None and parsed is not None,
        "raw_response_preserved": captured_raw is not None,
        "raw_response_hash_recorded": (OUT / "probe_raw.txt").is_file(),
        "lineage_complete": True,
        "authoritative_response": classification is None and parsed is not None,
        "quality_verdict": quality_verdict,
    }
    assessment = gate.complete_recovery_probe(evidence)
    metadata = json.loads((OUT / "probe_request_metadata.json").read_text(encoding="utf-8"))
    metadata.update({
        "status": "PASS" if assessment.passed else "PROVIDER_BLOCKED",
        "providerCalls": provider_calls,
        "successfulResponses": successful,
        "failedResponses": failed,
        "classification": classification,
        "rawSha256": sha_path(OUT / "probe_raw.txt") if (OUT / "probe_raw.txt").is_file() else None,
        "parsedSha256": sha_path(OUT / "probe_parsed.json") if (OUT / "probe_parsed.json").is_file() else None,
        "gateAssessment": {"passed": assessment.passed, "failedCriteria": list(assessment.failed_criteria), "qualityVerdict": assessment.quality_verdict},
    })
    write_json(OUT / "probe_request_metadata.json", metadata)
    write_json(OUT / "summary.json", {
        "taskId": "R1-P5-R1-PROVIDER-RECOVERY-PROBE",
        "status": "PASS" if assessment.passed else "PROVIDER_BLOCKED",
        "isProviderRecovered": assessment.passed,
        "providerRecoveryStatus": "PASS" if assessment.passed else "PROVIDER_BLOCKED",
        "providerHold": gate.state.value,
        "providerCalls": provider_calls,
        "successfulResponses": successful,
        "failedResponses": failed,
        "transportAttempts": 1,
        "retries": 0,
        "faceLocal": {"expected": 9, "valid": 0},
        "scenarioGlobal": {"expected": 9, "valid": 0},
        "pendingAuthoritativeEvaluations": 18,
        "boundary": boundary,
        "qualityDisposition": "UNVALIDATED",
        "nextAction": "AUTHORITATIVE_EVALUATION_RESUME_TASK" if assessment.passed else "KEEP_PROVIDER_HOLD_ACTIVE",
        "featureFlag": "OFF",
        "productionPromotion": "NO",
        "architectureChanged": False,
        "gpuJobs": 0,
        "nanoCalls": 0,
        "alternativeProviderCalls": 0,
        "gate": gate.snapshot(),
    })
    write_hashes()
    print(json.dumps({"status": "PASS" if assessment.passed else "PROVIDER_BLOCKED", "output": str(OUT), "providerCalls": provider_calls, "providerHold": gate.state.value}, ensure_ascii=False))
    return 0 if assessment.passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
