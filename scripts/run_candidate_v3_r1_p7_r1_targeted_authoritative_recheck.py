#!/usr/bin/env python3
"""Run the explicitly authorized R1-P7-R1 five-case authoritative recheck."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
PHASE7 = ROOT / "artifacts/identity-restoration/phase7-candidate-v3"
P7 = PHASE7 / "r1-p7-targeted-quality-remediation-20260902T030000Z"
P6 = PHASE7 / "r1-p6-authoritative-evaluation-resume-20260902T024012Z"
R4 = PHASE7 / "r1-p5-r4-provider-recovery-recheck-20260902T010010Z"
HOLD = PHASE7 / "r1-p4-r3-provider-hold-active.json"
P6_RUNNER_PATH = ROOT / "scripts/run_candidate_v3_r1_p6_authoritative_evaluation_resume.py"
OUT = Path(os.environ.get(
    "R1_P7_R1_OUTPUT_DIR",
    str(PHASE7 / ("r1-p7-r1-targeted-authoritative-recheck-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))),
))
TASK_ID = "R1-P7-R1-TARGETED-AUTHORITATIVE-RECHECK"
FACE_CASES = ("B05", "B07")
SCENARIO_CASES = ("B05", "B06", "B09")
MODEL = "gemini-flash-latest"
P7_COMMIT = "e7d81a8"


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_path(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def canonical_hash(value: Any) -> str:
    return sha_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def load_p6_runner() -> Any:
    spec = importlib.util.spec_from_file_location("candidate_v3_r1_p6_runner_for_r1", P6_RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load existing authoritative runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_offline(command: list[str]) -> tuple[int, str]:
    clean_env = dict(os.environ)
    clean_env.pop("VALIDATOR_LIVE_ENABLED", None)
    clean_env.pop("GEMINI_API_KEY", None)
    clean_env.pop("GOOGLE_API_KEY", None)
    result = subprocess.run(command, cwd=ROOT, env=clean_env, capture_output=True, text=True, check=False)
    return result.returncode, (result.stdout + result.stderr).rstrip() + "\n"


def finish_hashes() -> None:
    files = {
        str(path.relative_to(OUT)): sha_path(path)
        for path in sorted(OUT.rglob("*"))
        if path.is_file() and path.name != "hashes.sha256"
    }
    write_json(OUT / "hashes.sha256", {"algorithm": "SHA-256", "files": files, "count": len(files)})


def verify_r1_p7_state() -> dict[str, Any]:
    summary = json.loads((P7 / "summary.json").read_text(encoding="utf-8"))
    if summary.get("status") != "CLOSED / REMEDIATION_READY":
        raise RuntimeError("R1_P7_NOT_REMEDIATION_READY")
    if summary.get("qualityDisposition") != "FAIL_PENDING_RECHECK":
        raise RuntimeError("R1_P7_QUALITY_DISPOSITION_MISMATCH")
    if not (P7 / "hashes.sha256").is_file():
        raise RuntimeError("R1_P7_EVIDENCE_MISSING")
    return {
        "path": str(P7.relative_to(ROOT)),
        "summarySha256": sha_path(P7 / "summary.json"),
        "status": summary["status"],
        "qualityDisposition": summary["qualityDisposition"],
        "commit": P7_COMMIT,
    }


def verify_recovery(p6_module: Any) -> dict[str, Any]:
    recovery = p6_module.verify_recovery_evidence()
    if recovery["provider"] != "Gemini" or recovery["model"] != MODEL:
        raise RuntimeError("PROVIDER_LOCK_MISMATCH")
    return recovery


def manifest_cases() -> dict[str, dict[str, Any]]:
    payload = yaml.safe_load((ROOT / "contracts/identity_restoration/benchmark_set.yaml").read_text(encoding="utf-8"))
    return {str(item["id"]): item for item in payload["cases"]}


def case_paths(runner: Any, case_id: str) -> tuple[Path, Path, dict[str, Any]]:
    job, candidate, face_input, placeholder = runner.job_payload(case_id)
    return candidate, face_input, job


def make_sink(case_dir: Path, lane: str, case_id: str) -> Any:
    def sink(event: dict[str, Any]) -> None:
        append_jsonl(OUT / "attempt-history.jsonl", {
            "taskId": TASK_ID, "lane": lane, "caseId": case_id,
            "capturedAt": datetime.now(timezone.utc).isoformat(), **event,
        })
        raw = event.get("rawResponse")
        if raw is not None:
            raw_text = str(raw).rstrip("\n") + "\n"
            raw_path = case_dir / "raw_provider_response.txt"
            if raw_path.is_file() and raw_path.read_text(encoding="utf-8") != raw_text:
                raise RuntimeError(f"IMMUTABLE_RAW_EVIDENCE_CONFLICT:{raw_path}")
            raw_path.write_text(raw_text, encoding="utf-8")
        parsed = event.get("parsedEvidence")
        if parsed is not None:
            write_json(case_dir / "parsed_result.json", parsed)
    return sink


def run_case(runner: Any, cases: dict[str, dict[str, Any]], lane: str, case_id: str) -> dict[str, Any]:
    from identity_restoration.application.benchmark_orchestration import _scenario_profile_id
    from shared.vision.paid_call_guard import paid_call_context
    from shared.vision.providers.gemini_vision import classify_gemini_failure
    from validator_studio.face_validator import _assert_face_observation_contract, _load_face_rubric, validate_face
    from validator_studio.image_validator import validate_image
    from validator_studio.schemas.face_validation import FaceValidationObservation
    from validator_studio.schemas.image_validation import ImageObservation

    candidate, face_input, job = case_paths(runner, case_id)
    image_path = face_input if lane == "FACE_LOCAL" else candidate
    profile = _scenario_profile_id(cases[case_id])
    authority = "action_full_body" if profile == "action_full_body" else "canonical_default"
    case_dir = OUT / ("face_local" if lane == "FACE_LOCAL" else "scenario_global") / case_id
    input_hash = sha_path(image_path)
    descriptor = runner.descriptor(lane, case_id, 1, input_hash, authority, profile, MODEL)
    metadata = {
        "taskId": TASK_ID, "caseId": case_id, "lane": lane,
        "inputId": str(image_path.relative_to(ROOT)), "inputSha256": input_hash,
        "provider": "Gemini", "model": MODEL, "evaluatorVersion": runner.VALIDATOR_VERSION,
        "authorityProfile": authority, "validatorProfile": profile,
        "referenceArtifacts": [{"path": str(runner.A2_PATH.relative_to(ROOT)), "sha256": runner.A2_SHA}] if lane == "FACE_LOCAL" else [],
        "descriptor": descriptor, "callStatus": "STARTED", "validResponse": False,
        "lineage": "VERIFIED", "lineageToR1P6Failure": f"R1-P6/{lane}/{case_id}",
        "remediationSource": "R1-P7 targeted binding/variant plan",
        "frozenInputPreserved": True,
    }
    write_json(case_dir / "request_metadata.json", metadata)
    sink = make_sink(case_dir, lane, case_id)
    try:
        with paid_call_context({
            "benchmarkId": TASK_ID, "branch": lane, "imageSha256": input_hash,
            "sampleIndex": 1, "reason": "authorized R1-P7-R1 targeted authoritative recheck",
            "historicalEvidenceSearch": {"exactArtifactCacheMatch": False, "lineage": "VERIFIED"},
        }):
            if lane == "FACE_LOCAL":
                report = validate_face(
                    "venho_hotel", "linh_an", image_path, provider="gemini",
                    reference_image_paths=[runner.A2_PATH], samples=1,
                    raw_response_sink=sink,
                    validation_cycle_id=f"candidate-v3-r1-p7-r1-{case_id.lower()}-face-1",
                    attempt_id="r1-p7-r1",
                )
                observation = FaceValidationObservation.model_validate(report.raw_observation)
                _assert_face_observation_contract(observation.model_dump(mode="json"), _load_face_rubric("venho_hotel"))
            else:
                report = validate_image(
                    "venho_hotel", "linh_an", image_path, provider="gemini", samples=1,
                    scenario_profile_id=profile, raw_response_sink=sink,
                )
                ImageObservation.model_validate(report.raw_observation)
    except Exception as exc:
        reason = classify_gemini_failure(exc)
        raw_path = case_dir / "raw_provider_response.txt"
        metadata.update({"callStatus": "INVALID", "validResponse": False, "invalidReason": reason,
                         "error": str(exc), "rawHash": sha_path(raw_path) if raw_path.is_file() else None})
        write_json(case_dir / "request_metadata.json", metadata)
        return {"caseId": case_id, "lane": lane, "inputId": metadata["inputId"], "provider": "Gemini",
                "model": MODEL, "evaluatorVersion": runner.VALIDATOR_VERSION, "callStatus": "INVALID",
                "validResponse": False, "invalidReason": reason, "rawHash": metadata["rawHash"],
                "parsedHash": None, "lineage": "VERIFIED", "qualityPass": None, "score": None, "verdict": None}

    report_data = report.model_dump(mode="json")
    raw_path = case_dir / "raw_provider_response.txt"
    parsed_path = case_dir / "parsed_result.json"
    raw_hash = sha_path(raw_path) if raw_path.is_file() else None
    parsed_hash = sha_path(parsed_path) if parsed_path.is_file() else None
    if raw_hash is None or parsed_hash is None:
        raise RuntimeError(f"MISSING_VALID_RESULT_EVIDENCE:{lane}/{case_id}")
    score = float(report_data["overall_score"])
    quality_pass = score >= 90.0
    write_json(case_dir / "evaluation_report.json", report_data)
    metadata.update({"callStatus": "SUCCESS", "validResponse": True, "score": score,
                     "verdict": report_data["verdict"], "qualityPass": quality_pass,
                     "rawHash": raw_hash, "parsedHash": parsed_hash, "reportHash": canonical_hash(report_data)})
    write_json(case_dir / "request_metadata.json", metadata)
    return {"caseId": case_id, "lane": lane, "inputId": metadata["inputId"], "provider": "Gemini",
            "model": MODEL, "evaluatorVersion": runner.VALIDATOR_VERSION, "callStatus": "SUCCESS",
            "validResponse": True, "score": score, "verdict": report_data["verdict"],
            "qualityPass": quality_pass, "rawHash": raw_hash, "parsedHash": parsed_hash, "lineage": "VERIFIED"}


def ledger_rows() -> list[dict[str, Any]]:
    path = OUT / "provider-paid-call-ledger.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    if os.environ.get("TARGETED_RECHECK_AUTHORIZED") != "TRUE":
        write_json(OUT / "targeted_recheck_summary.json", {"taskId": TASK_ID, "status": "BLOCKED_AUTHORIZATION", "providerCalls": 0})
        finish_hashes()
        return 2

    p6_module = load_p6_runner()
    runner = p6_module.load_runner()
    p7_state = verify_r1_p7_state()
    recovery = verify_recovery(p6_module)
    baseline = {
        "taskId": TASK_ID,
        "authorization": {"name": "TARGETED_RECHECK_AUTHORIZED", "requiredValue": "TRUE", "receivedValue": os.environ.get("TARGETED_RECHECK_AUTHORIZED")},
        "r1P7Evidence": p7_state,
        "startState": {"r1P7": "CLOSED / REMEDIATION_READY", "qualityDisposition": "FAIL_PENDING_RECHECK",
                        "boundary": "9/9 PASS", "faceLocal": "7 PASS / 2 FAIL (B05, B07)",
                        "scenarioGlobal": "6 PASS / 3 FAIL (B05, B06, B09)", "featureFlag": "OFF",
                        "productionPromotion": "NO", "architectureChanged": False},
        "recoveryEvidence": recovery,
        "scope": {"faceLocal": list(FACE_CASES), "scenarioGlobal": list(SCENARIO_CASES), "maxProviderCalls": 5, "retries": 0},
    }
    write_json(OUT / "baseline.json", baseline)

    focused_tests = [
        "tests/test_candidate_v3_r1_p7_targeted_remediation.py",
        "tests/test_gw_p4_r1_t3_authority.py",
        "tests/test_candidate_v3_r1_p6_authoritative_evaluation_resume.py",
        "tests/test_candidate_v3_r1_p5_provider_recovery_gate.py",
        "tests/identity_restoration/application/test_phase7_candidate_v3_evaluation.py",
        "tests/identity_restoration/application/test_benchmark_orchestration.py",
        "tests/identity_restoration/contracts/test_candidate_v3_schemas.py",
    ]
    test_code, test_output = run_offline(["python3", "-m", "pytest", "-q", *focused_tests])
    compile_code, compile_output = run_offline(["python3", "-m", "compileall", "-q", "identity_restoration", "validator_studio", "shared/vision", "scripts/run_candidate_v3_r1_p7_r1_targeted_authoritative_recheck.py"])
    diff_code, diff_output = run_offline(["git", "diff", "--check"])
    (OUT / "test_results.txt").write_text(test_output, encoding="utf-8")
    (OUT / "compileall.txt").write_text((compile_output if compile_output.strip() else "compileall=PASS\n") if compile_code == 0 else compile_output, encoding="utf-8")
    (OUT / "git_diff_check.txt").write_text((diff_output if diff_output.strip() else "git_diff_check=PASS\n") if diff_code == 0 else diff_output, encoding="utf-8")
    preflight_status = "PASS" if test_code == compile_code == diff_code == 0 else "BLOCKED_LOCAL_REGRESSION"
    write_json(OUT / "offline_preflight.json", {
        "status": preflight_status, "providerCalls": 0, "testsExitCode": test_code,
        "compileallExitCode": compile_code, "gitDiffCheckExitCode": diff_code,
        "provider": recovery["provider"], "model": recovery["model"],
        "lineage": "targeted five-case inputs verified against R1-P6/R1-P7",
    })
    if preflight_status != "PASS":
        write_json(OUT / "targeted_recheck_summary.json", {"taskId": TASK_ID, "status": "BLOCKED_LOCAL_REGRESSION", "providerCalls": 0})
        finish_hashes()
        return 2

    runner.load_env()
    os.environ["VALIDATOR_LIVE_ENABLED"] = "true"
    os.environ["VALIDATOR_MAX_NEW_CALLS"] = "5"
    os.environ["GEMINI_MAX_TRANSPORT_ATTEMPTS"] = "1"
    os.environ["GEMINI_VISION_MODEL"] = MODEL
    os.environ["VALIDATOR_PAID_CALL_LEDGER"] = str(OUT / "provider-paid-call-ledger.jsonl")
    cases = manifest_cases()
    face_results: list[dict[str, Any]] = []
    scenario_results: list[dict[str, Any]] = []
    blocker: str | None = None
    for case_id in FACE_CASES:
        result = run_case(runner, cases, "FACE_LOCAL", case_id)
        face_results.append(result)
        if not result["validResponse"]:
            blocker = result.get("invalidReason") or "INVALID_TARGETED_RESPONSE"
            break
    face_stable = blocker is None and len(face_results) == 2 and all(item["validResponse"] for item in face_results)
    write_json(OUT / "face_local" / "stability_gate.json", {"status": "PASS" if face_stable else "BLOCKED", "expected": 2, "valid": sum(item["validResponse"] for item in face_results), "blocker": blocker})
    if face_stable:
        for case_id in SCENARIO_CASES:
            result = run_case(runner, cases, "SCENARIO_GLOBAL", case_id)
            scenario_results.append(result)
            if not result["validResponse"]:
                blocker = result.get("invalidReason") or "INVALID_TARGETED_RESPONSE"
                break

    ledger = ledger_rows()
    provider_calls = sum(row.get("event") == "intent" for row in ledger)
    valid_face = sum(item["validResponse"] for item in face_results)
    valid_scenario = sum(item["validResponse"] for item in scenario_results)
    face_pass = sum(item.get("qualityPass") is True for item in face_results)
    scenario_pass = sum(item.get("qualityPass") is True for item in scenario_results)
    targeted_complete = valid_face == 2 and valid_scenario == 3 and blocker is None
    task_status = "CLOSED / PASS" if targeted_complete else "PROVIDER_BLOCKED_PARTIAL"
    quality = "PASS" if targeted_complete and face_pass == 2 and scenario_pass == 3 else "FAIL" if targeted_complete else "FAIL_PENDING_RECHECK"
    if targeted_complete:
        final_face = {"pass": 7 + face_pass, "fail": 2 - face_pass}
        final_scenario = {"pass": 6 + scenario_pass, "fail": 3 - scenario_pass}
    else:
        final_face = {"pass": 7, "fail": 2}
        final_scenario = {"pass": 6, "fail": 3}
    write_json(OUT / "provider_call_accounting.json", {
        "provider": recovery["provider"], "model": recovery["model"], "maxProviderCalls": 5,
        "providerCalls": provider_calls, "retries": 0,
        "faceLocalCalls": len(face_results), "scenarioGlobalCalls": len(scenario_results),
        "faceLocalExpected": 2, "scenarioGlobalExpected": 3,
        "gpuJobs": 0, "nanoCalls": 0, "alternativeProviderCalls": 0,
        "ledgerIntents": sum(row.get("event") == "intent" for row in ledger),
        "ledgerResults": sum(row.get("event") == "result" for row in ledger),
    })
    write_json(OUT / "targeted_recheck_summary.json", {
        "taskId": TASK_ID, "status": task_status, "providerCalls": provider_calls, "retries": 0,
        "faceLocal": {"cases": list(FACE_CASES), "expected": 2, "attempted": len(face_results), "valid": valid_face, "invalid": len(face_results) - valid_face, "pass": face_pass, "fail": len(face_results) - face_pass, "results": face_results},
        "scenarioGlobal": {"cases": list(SCENARIO_CASES), "expected": 3, "attempted": len(scenario_results), "valid": valid_scenario, "invalid": len(scenario_results) - valid_scenario, "pass": scenario_pass, "fail": len(scenario_results) - scenario_pass, "results": scenario_results},
        "stabilityGate": "PASS" if face_stable else "BLOCKED", "pendingTargeted": 5 - valid_face - valid_scenario,
        "boundary": "9/9 PASS", "finalFaceLocalBaselinePlusTargeted": final_face,
        "finalScenarioGlobalBaselinePlusTargeted": final_scenario, "qualityDisposition": quality,
        "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False,
        "nextAction": "PROMOTION_READINESS_REVIEW_REQUIRES_SEPARATE_AUTHORIZATION" if quality == "PASS" else "TARGETED_REMEDIATION_R2_REQUIRES_SEPARATE_AUTHORIZATION" if quality == "FAIL" else "KEEP_PROVIDER_HOLD_ACTIVE",
    })
    before_after = {"source": str(P6.relative_to(ROOT)), "targetedOnly": True, "cases": {"FACE_LOCAL": {}, "SCENARIO_GLOBAL": {}}}
    for lane, results in (("FACE_LOCAL", face_results), ("SCENARIO_GLOBAL", scenario_results)):
        for result in results:
            number = int(result["caseId"][1:])
            old = json.loads((P6 / lane.lower() / f"case-{number:02d}" / "request_metadata.json").read_text(encoding="utf-8"))
            before_after["cases"][lane][result["caseId"]] = {"before": {"score": old["score"], "verdict": old["verdict"], "rawHash": old["rawHash"], "parsedHash": old["parsedHash"]}, "after": result}
    write_json(OUT / "before_after_comparison.json", before_after)
    write_json(OUT / "quality_disposition.json", {
        "taskId": TASK_ID, "r1P7R1": task_status, "qualityDisposition": quality,
        "boundary": "9/9 PASS", "faceLocal": {"valid": valid_face, "pass": face_pass, "fail": len(face_results) - face_pass},
        "scenarioGlobal": {"valid": valid_scenario, "pass": scenario_pass, "fail": len(scenario_results) - scenario_pass},
        "pendingAuthoritativeEvaluations": 0 if targeted_complete else 5 - valid_face - valid_scenario,
        "aggregationPolicy": "existing approved score threshold >= 90.0; no policy change",
        "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False,
    })
    finish_hashes()
    print(json.dumps({"status": task_status, "output": str(OUT), "providerCalls": provider_calls, "faceValid": valid_face, "scenarioValid": valid_scenario, "qualityDisposition": quality}))
    return 0 if targeted_complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
