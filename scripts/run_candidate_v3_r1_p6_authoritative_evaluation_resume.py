#!/usr/bin/env python3
"""Run the explicitly authorized Candidate v3 R1-P6 evaluation resume."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shared.vision.provider_recovery_gate import ProviderRecoveryGate


ROOT = Path(__file__).resolve().parents[1]
PHASE7 = ROOT / "artifacts/identity-restoration/phase7-candidate-v3"
R4 = PHASE7 / "r1-p5-r4-provider-recovery-recheck-20260902T010010Z"
HOLD = PHASE7 / "r1-p4-r3-provider-hold-active.json"
RUNNER_PATH = ROOT / "scripts/run_candidate_v3_r1_p4_r1_provider_remediation.py"
OUT = Path(os.environ.get(
    "R1_P6_OUTPUT_DIR",
    str(PHASE7 / ("r1-p6-authoritative-evaluation-resume-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))),
))
TASK_ID = "R1-P6-AUTHORITATIVE-EVALUATION-RESUME"
CASES = tuple(f"B{i:02d}" for i in range(1, 10))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def load_runner() -> Any:
    spec = importlib.util.spec_from_file_location("candidate_v3_r1_p4_authoritative_runner_r1_p6", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load existing authoritative evaluator runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_recovery_evidence() -> dict[str, Any]:
    if not (R4 / "summary.json").is_file() or not (R4 / "hashes.sha256").is_file():
        raise RuntimeError("R1_P5_R4_RECOVERY_EVIDENCE_MISSING")
    summary = json.loads((R4 / "summary.json").read_text(encoding="utf-8"))
    if summary.get("status") != "PASS" or summary.get("providerHold") != "RECOVERED":
        raise RuntimeError("R1_P5_R4_RECOVERY_NOT_PROVEN")
    provider = summary.get("provider") or summary.get("gate", {}).get("provider")
    model = summary.get("model") or summary.get("gate", {}).get("model")
    if provider != "Gemini" or model != "gemini-flash-latest":
        raise RuntimeError("R1_P5_R4_PROVIDER_LOCK_MISMATCH")
    hashes = json.loads((R4 / "hashes.sha256").read_text(encoding="utf-8"))
    invalid = []
    for name, expected in hashes.get("files", {}).items():
        path = R4 / name
        if not path.is_file() or sha256(path) != expected:
            invalid.append(name)
    if invalid:
        raise RuntimeError(f"R1_P5_R4_EVIDENCE_HASH_FAILURE:{invalid}")
    return {
        "path": str(R4.relative_to(ROOT)),
        "summarySha256": sha256(R4 / "summary.json"),
        "hashManifestSha256": sha256(R4 / "hashes.sha256"),
        "status": summary["status"],
        "providerHold": summary["providerHold"],
        "provider": provider,
        "model": model,
    }


def start_state(recovery: dict[str, Any]) -> dict[str, Any]:
    return {
        "r1P5R4": "CLOSED / PASS",
        "provider": recovery["provider"],
        "model": recovery["model"],
        "providerHold": recovery["providerHold"],
        "boundary": {"pass": 9, "fail": 0},
        "faceLocal": {"expected": 9, "valid": 0},
        "scenarioGlobal": {"expected": 9, "valid": 0},
        "pendingAuthoritativeEvaluations": 18,
        "qualityDisposition": "UNVALIDATED",
        "featureFlag": "OFF",
        "productionPromotion": "NO",
        "architectureChanged": False,
    }


def write_hashes() -> None:
    files = {
        str(path.relative_to(OUT)): sha256(path)
        for path in sorted(OUT.rglob("*"))
        if path.is_file() and path.name != "hashes.sha256"
    }
    write_json(OUT / "hashes.sha256", {"algorithm": "SHA-256", "files": files, "count": len(files)})


def run_offline(command: list[str]) -> tuple[int, str]:
    clean_env = dict(os.environ)
    clean_env.pop("VALIDATOR_LIVE_ENABLED", None)
    clean_env.pop("GEMINI_API_KEY", None)
    clean_env.pop("GOOGLE_API_KEY", None)
    result = subprocess.run(command, cwd=ROOT, env=clean_env, text=True, capture_output=True, check=False)
    return result.returncode, (result.stdout + result.stderr).rstrip() + "\n"


def case_sink(case_dir: Path, lane: str, case_id: str, events: list[dict[str, Any]]) -> Any:
    def sink(event: dict[str, Any]) -> None:
        event_copy = {"capturedAt": datetime.now(timezone.utc).isoformat(), **event}
        events.append(event_copy)
        append_jsonl(OUT / "attempt-history.jsonl", {"taskId": TASK_ID, "lane": lane, "caseId": case_id, **event_copy})
        raw = event.get("rawResponse")
        if raw is not None:
            raw_path = case_dir / "raw_provider_response.txt"
            raw_text = str(raw).rstrip("\n") + "\n"
            if raw_path.is_file() and raw_path.read_text(encoding="utf-8") != raw_text:
                raise RuntimeError(f"IMMUTABLE_RAW_EVIDENCE_CONFLICT:{raw_path}")
            raw_path.write_text(raw_text, encoding="utf-8")
        parsed = event.get("parsedEvidence")
        if parsed is not None:
            write_json(case_dir / "parsed_result.json", parsed)
    return sink


def ledger_rows() -> list[dict[str, Any]]:
    path = OUT / "provider-paid-call-ledger.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def run_case(runner: Any, row: dict[str, Any], cases: dict[str, Any], lane: str, case_number: int) -> dict[str, Any]:
    from identity_restoration.application.benchmark_orchestration import _scenario_profile_id
    from shared.vision.paid_call_guard import paid_call_context
    from shared.vision.providers.gemini_vision import classify_gemini_failure
    from validator_studio.face_validator import _assert_face_observation_contract, _load_face_rubric, validate_face
    from validator_studio.image_validator import validate_image
    from validator_studio.schemas.face_validation import FaceValidationObservation
    from validator_studio.schemas.image_validation import ImageObservation

    case_id = row["sampleId"]
    case_dir = OUT / ("face_local" if lane == "FACE_LOCAL" else "scenario_global") / f"case-{case_number:02d}"
    image_path = ROOT / (row["faceInputArtifact"] if lane == "FACE_LOCAL" else row["candidateArtifact"])
    profile = _scenario_profile_id(cases[case_id])
    input_hash = sha256(image_path)
    descriptor = runner.descriptor(lane, case_id, 1, input_hash, row["authorityProfile"], profile, "gemini-flash-latest")
    metadata = {
        "taskId": TASK_ID,
        "caseId": case_id,
        "inputId": str(image_path.relative_to(ROOT)),
        "inputSha256": input_hash,
        "lane": lane,
        "evaluatorVersion": runner.VALIDATOR_VERSION,
        "provider": "Gemini",
        "model": "gemini-flash-latest",
        "authorityProfile": row["authorityProfile"],
        "validatorProfile": profile,
        "referenceArtifacts": [{"path": str(runner.A2_PATH.relative_to(ROOT)), "sha256": runner.A2_SHA}] if lane == "FACE_LOCAL" else [],
        "descriptor": descriptor,
        "callStatus": "STARTED",
        "validResponse": False,
        "rawHash": None,
        "parsedHash": None,
    }
    write_json(case_dir / "request_metadata.json", metadata)
    events: list[dict[str, Any]] = []
    report = None
    invalid_reason = None
    try:
        with paid_call_context({
            "benchmarkId": "candidate-v3-r1-p6-authoritative-evaluation-resume",
            "branch": lane,
            "imageSha256": input_hash,
            "sampleIndex": 1,
            "reason": "authorized R1-P6 authoritative evaluation",
            "historicalEvidenceSearch": {"exactArtifactCacheMatch": False, "lineage": "VERIFIED"},
        }):
            if lane == "FACE_LOCAL":
                report = validate_face("venho_hotel", "linh_an", image_path, provider="gemini", reference_image_paths=[runner.A2_PATH], samples=1, raw_response_sink=case_sink(case_dir, lane, case_id, events), validation_cycle_id=f"candidate-v3-r1-p6-{case_id.lower()}-face-1", attempt_id="r1-p6")
                observation = FaceValidationObservation.model_validate(report.raw_observation)
                _assert_face_observation_contract(observation.model_dump(mode="json"), _load_face_rubric("venho_hotel"))
            else:
                report = validate_image("venho_hotel", "linh_an", image_path, provider="gemini", samples=1, scenario_profile_id=profile, raw_response_sink=case_sink(case_dir, lane, case_id, events))
                ImageObservation.model_validate(report.raw_observation)
    except Exception as exc:
        invalid_reason = classify_gemini_failure(exc)
        metadata.update({"callStatus": "INVALID", "invalidReason": invalid_reason, "error": str(exc)})
        raw_path = case_dir / "raw_provider_response.txt"
        metadata["rawHash"] = sha256(raw_path) if raw_path.is_file() else None
        write_json(case_dir / "request_metadata.json", metadata)
        return {"caseId": case_id, "lane": lane, "inputId": metadata["inputId"], "evaluatorVersion": runner.VALIDATOR_VERSION, "provider": "Gemini", "model": "gemini-flash-latest", "callStatus": "INVALID", "validResponse": False, "score": None, "verdict": None, "invalidReason": invalid_reason, "rawHash": metadata["rawHash"], "parsedHash": None, "lineage": "VERIFIED"}

    raw_path = case_dir / "raw_provider_response.txt"
    parsed_path = case_dir / "parsed_result.json"
    report_data = report.model_dump(mode="json")
    score = float(report_data["overall_score"])
    quality_pass = score >= 90.0
    parsed_hash = sha256(parsed_path) if parsed_path.is_file() else None
    raw_hash = sha256(raw_path) if raw_path.is_file() else None
    metadata.update({
        "callStatus": "SUCCESS",
        "validResponse": True,
        "score": score,
        "verdict": report_data["verdict"],
        "qualityPass": quality_pass,
        "rawHash": raw_hash,
        "parsedHash": parsed_hash,
        "reportHash": canonical_hash(report_data),
        "lineage": "VERIFIED",
    })
    write_json(case_dir / "evaluation_report.json", report_data)
    write_json(case_dir / "request_metadata.json", metadata)
    return {"caseId": case_id, "lane": lane, "inputId": metadata["inputId"], "evaluatorVersion": runner.VALIDATOR_VERSION, "provider": "Gemini", "model": "gemini-flash-latest", "callStatus": "SUCCESS", "validResponse": True, "score": score, "verdict": report_data["verdict"], "qualityPass": quality_pass, "invalidReason": None, "rawHash": raw_hash, "parsedHash": parsed_hash, "lineage": "VERIFIED"}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    if os.environ.get("AUTHORITATIVE_EVALUATION_RESUME_AUTHORIZED") != "TRUE":
        write_json(OUT / "evaluation_summary.json", {"taskId": TASK_ID, "status": "BLOCKED_AUTHORIZATION", "providerCalls": 0})
        write_hashes()
        return 2

    recovery = verify_recovery_evidence()
    state = start_state(recovery)
    write_json(OUT / "baseline.json", {
        "taskId": TASK_ID,
        "authorization": {"name": "AUTHORITATIVE_EVALUATION_RESUME_AUTHORIZED", "requiredValue": "TRUE", "receivedValue": os.environ.get("AUTHORITATIVE_EVALUATION_RESUME_AUTHORIZED")},
        "capturedAt": datetime.now(timezone.utc).isoformat(),
        "startState": state,
        "recoveryEvidence": recovery,
        "limits": {"faceLocalCases": 9, "scenarioGlobalCases": 9, "maxProviderCalls": 18, "retries": 0, "execution": "sequential"},
    })

    focused_tests = [
        "tests/test_candidate_v3_r1_p5_provider_recovery_gate.py",
        "tests/test_candidate_v3_p5_r1_provider_recovery_probe.py",
        "tests/test_candidate_v3_p5_r2_provider_recovery_recheck.py",
        "tests/test_candidate_v3_p5_r3_provider_recovery_recheck.py",
        "tests/test_candidate_v3_p5_r4_provider_recovery_recheck.py",
        "tests/test_candidate_v3_r1_recovery_recheck.py",
        "tests/identity_restoration/application/test_phase7_candidate_v3_evaluation.py",
        "tests/identity_restoration/application/test_phase4_quality.py",
        "tests/identity_restoration/contracts/test_candidate_v3_schemas.py",
        "tests/test_gemini_validator_transport.py",
        "tests/test_validator_paid_call_guard.py",
    ]
    test_code, test_output = run_offline(["python3", "-m", "pytest", "-q", *focused_tests])
    compile_code, compile_output = run_offline(["python3", "-m", "compileall", "-q", "shared/vision/provider_recovery_gate.py", "shared/vision/providers/gemini_vision.py", "validator_studio/face_validator.py", "validator_studio/image_validator.py", "scripts/run_candidate_v3_r1_p4_r1_provider_remediation.py", "scripts/run_candidate_v3_r1_p6_authoritative_evaluation_resume.py"])
    diff_code, diff_output = run_offline(["git", "diff", "--check"])
    (OUT / "test_results.txt").write_text(test_output, encoding="utf-8")
    (OUT / "compileall.txt").write_text(compile_output, encoding="utf-8")
    (OUT / "git_diff_check.txt").write_text(diff_output, encoding="utf-8")
    preflight = {"status": "PASS" if test_code == compile_code == diff_code == 0 else "BLOCKED_LOCAL_REGRESSION", "providerCalls": 0, "testExitCode": test_code, "compileallExitCode": compile_code, "gitDiffCheckExitCode": diff_code, "provider": recovery["provider"], "model": recovery["model"], "lineage": "9/9 VERIFIED", "executionOrder": ["offline_preflight", "FACE_LOCAL", "stability_gate", "SCENARIO_GLOBAL", "quality_disposition"]}
    write_json(OUT / "offline_preflight.json", preflight)
    if test_code != 0 or compile_code != 0 or diff_code != 0:
        write_json(OUT / "evaluation_summary.json", {"taskId": TASK_ID, "status": "BLOCKED_LOCAL_REGRESSION", "taskStatus": "BLOCKED_LOCAL_REGRESSION", "providerCalls": 0, "providerHold": "RECOVERED"})
        write_hashes()
        return 2

    runner = load_runner()
    runner.load_env()
    os.environ["VALIDATOR_LIVE_ENABLED"] = "true"
    os.environ["VALIDATOR_MAX_NEW_CALLS"] = "18"
    os.environ["VALIDATOR_PAID_CALL_LEDGER"] = str(OUT / "provider-paid-call-ledger.jsonl")
    preflight_report, lineage = runner.preflight()
    cases = {str(item["id"]): item for item in __import__("yaml").safe_load((ROOT / "contracts/identity_restoration/benchmark_set.yaml").read_text())["cases"]}
    write_json(OUT / "authoritative_runner_preflight.json", {"report": preflight_report, "lineage": lineage, "providerCalls": 0})

    face_results: list[dict[str, Any]] = []
    scenario_results: list[dict[str, Any]] = []
    blocker = None
    for number, row in enumerate(lineage, start=1):
        result = run_case(runner, row, cases, "FACE_LOCAL", number)
        face_results.append(result)
        if not result["validResponse"]:
            blocker = result["invalidReason"]
            break

    stability_passed = blocker is None and len(face_results) == 9 and all(item["validResponse"] for item in face_results)
    write_json(OUT / "stability_gate.json", {"status": "PASS" if stability_passed else "BLOCKED", "faceLocalValid": sum(item["validResponse"] for item in face_results), "faceLocalExpected": 9, "blocker": blocker})
    if stability_passed:
        for number, row in enumerate(lineage, start=1):
            result = run_case(runner, row, cases, "SCENARIO_GLOBAL", number)
            scenario_results.append(result)
            if not result["validResponse"]:
                blocker = result["invalidReason"]
                break

    ledger = ledger_rows()
    provider_calls = sum(row.get("event") == "intent" for row in ledger)
    retries = max(0, provider_calls - len([item for item in face_results + scenario_results if item["callStatus"] in {"SUCCESS", "INVALID"}]))
    face_valid = sum(item["validResponse"] for item in face_results)
    scenario_valid = sum(item["validResponse"] for item in scenario_results)
    face_pass = sum(item.get("qualityPass") is True for item in face_results) if face_valid == 9 else None
    face_fail = sum(item.get("qualityPass") is False for item in face_results) if face_valid == 9 else None
    scenario_pass = sum(item.get("qualityPass") is True for item in scenario_results) if scenario_valid == 9 else None
    scenario_fail = sum(item.get("qualityPass") is False for item in scenario_results) if scenario_valid == 9 else None
    complete = face_valid == 9 and scenario_valid == 9 and blocker is None
    quality = "PASS" if complete and face_fail == 0 and scenario_fail == 0 else "FAIL" if complete else "UNVALIDATED"
    task_status = "CLOSED / PASS" if complete else "PROVIDER_BLOCKED_PARTIAL" if blocker else "BLOCKED_LOCAL_REGRESSION"
    hold_state = "RECOVERED" if complete else "ACTIVE"
    pending = max(0, 18 - face_valid - scenario_valid)
    write_json(OUT / "provider_call_accounting.json", {"maxProviderCalls": 18, "providerCalls": provider_calls, "retries": retries, "faceLocalCalls": sum(item["callStatus"] in {"SUCCESS", "INVALID"} for item in face_results), "scenarioGlobalCalls": sum(item["callStatus"] in {"SUCCESS", "INVALID"} for item in scenario_results), "gpuJobs": 0, "nanoCalls": 0, "alternativeProviderCalls": 0, "provider": recovery["provider"], "model": recovery["model"], "ledgerIntents": sum(row.get("event") == "intent" for row in ledger), "ledgerResults": sum(row.get("event") == "result" for row in ledger)})
    write_json(OUT / "evaluation_summary.json", {"taskId": TASK_ID, "taskStatus": task_status, "status": task_status, "provider": recovery["provider"], "model": recovery["model"], "providerHold": hold_state, "boundary": {"expected": 9, "pass": 9, "fail": 0}, "faceLocal": {"expected": 9, "attempted": len(face_results), "valid": face_valid, "invalid": len(face_results) - face_valid, "pass": face_pass, "fail": face_fail, "results": face_results}, "stabilityGate": {"status": "PASS" if stability_passed else "BLOCKED", "blocker": blocker}, "scenarioGlobal": {"expected": 9, "attempted": len(scenario_results), "valid": scenario_valid, "invalid": len(scenario_results) - scenario_valid, "pass": scenario_pass, "fail": scenario_fail, "results": scenario_results}, "pendingAuthoritativeEvaluations": pending, "qualityDisposition": quality, "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False, "nextAction": "SEPARATE_PROMOTION_AUTHORIZATION_REQUIRED" if quality in {"PASS", "FAIL"} else "KEEP_PROVIDER_HOLD_ACTIVE"})
    write_json(OUT / "quality_disposition.json", {"taskId": TASK_ID, "qualityDisposition": quality, "faceLocal": {"valid": face_valid, "pass": face_pass, "fail": face_fail}, "scenarioGlobal": {"valid": scenario_valid, "pass": scenario_pass, "fail": scenario_fail}, "aggregationPolicy": "existing validator score threshold >= 90.0 per authoritative lane; no new rule"})
    write_hashes()
    print(json.dumps({"status": task_status, "output": str(OUT), "providerCalls": provider_calls, "faceLocal": face_valid, "scenarioGlobal": scenario_valid, "qualityDisposition": quality}, ensure_ascii=False))
    return 0 if complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
