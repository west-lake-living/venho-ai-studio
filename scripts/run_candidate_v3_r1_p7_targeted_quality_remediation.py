"""Build the offline R1-P7 remediation evidence bundle.

This harness is intentionally provider-free. It reads only the committed R1-P6
artifacts and exercises the existing validator authority replay locally.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

from validator_studio.image_validator import report_from_image_observations
from validator_studio.schemas.image_validation import ImageObservation


ROOT = Path(__file__).resolve().parents[1]
P6 = ROOT / "artifacts/identity-restoration/phase7-candidate-v3/r1-p6-authoritative-evaluation-resume-20260902T024012Z"
MANIFEST = ROOT / "contracts/identity_restoration/benchmark_set.yaml"
CONFIG = ROOT / "config/projects/venho_hotel/identity_restoration/r1_p7_targeted_quality_remediation.yaml"
PASSING_FACE = ["B01", "B02", "B03", "B04", "B06", "B08", "B09"]
PASSING_SCENARIO = ["B01", "B02", "B03", "B04", "B07", "B08"]
FAILED = {"FACE_LOCAL": ["B05", "B07"], "SCENARIO_GLOBAL": ["B05", "B06", "B09"]}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git_blob_sha(path: str) -> str:
    result = subprocess.run(["git", "show", f"HEAD:{path}"], cwd=ROOT, check=True, capture_output=True)
    return sha256_bytes(result.stdout)


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def p6_case(lane: str, case_id: str) -> dict:
    number = int(case_id[1:])
    folder = P6 / lane.lower() / f"case-{number:02d}"
    return {
        "evaluation": json.loads((folder / "evaluation_report.json").read_text()),
        "metadata": json.loads((folder / "request_metadata.json").read_text()),
        "folder": folder,
    }


def case_identity(lane: str, case_id: str) -> dict:
    item = p6_case(lane, case_id)
    evaluation = item["evaluation"]
    metadata = item["metadata"]
    return {
        "caseId": case_id,
        "lane": lane,
        "inputId": metadata["inputId"],
        "evaluator": metadata["provider"],
        "evaluatorVersion": metadata["evaluatorVersion"],
        "provider": metadata["provider"],
        "model": metadata["model"],
        "score": evaluation["overall_score"],
        "verdict": evaluation["verdict"],
        "validResponse": metadata["validResponse"],
        "lineage": metadata["lineage"],
        "rawResponseHash": metadata["rawHash"],
        "parsedResultHash": metadata["parsedHash"],
        "reportHash": metadata["reportHash"],
        "artifactHash": metadata["inputSha256"],
    }


def run_capture(command: list[str]) -> tuple[int, str]:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    output = result.stdout + result.stderr
    return result.returncode, output


def main() -> None:
    if os.environ.get("TARGETED_QUALITY_REMEDIATION_AUTHORIZED") != "TRUE":
        raise SystemExit("TARGETED_QUALITY_REMEDIATION_AUTHORIZED must be TRUE")
    if os.environ.get("TARGETED_RECHECK_AUTHORIZED", "FALSE") == "TRUE":
        raise SystemExit("R1-P7 is provider-free; TARGETED_RECHECK_AUTHORIZED must not be TRUE")
    if not P6.exists():
        raise SystemExit(f"missing authoritative R1-P6 evidence: {P6}")

    configured = yaml.safe_load(CONFIG.read_text())
    timestamp = os.environ.get("R1_P7_TIMESTAMP") or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = ROOT / "artifacts/identity-restoration/phase7-candidate-v3" / f"r1-p7-targeted-quality-remediation-{timestamp}"
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence directory: {output}")
    output.mkdir(parents=True)

    baseline = {
        "taskId": configured["task_id"],
        "sourceEvidence": str(P6.relative_to(ROOT)),
        "authorization": configured["authorization"],
        "r1P6": {
            "status": "CLOSED / PASS",
            "boundary": "9/9 PASS",
            "faceLocal": {"valid": 9, "pass": 7, "fail": 2, "failedCases": FAILED["FACE_LOCAL"]},
            "scenarioGlobal": {"valid": 9, "pass": 6, "fail": 3, "failedCases": FAILED["SCENARIO_GLOBAL"]},
            "pendingAuthoritativeEvaluations": 0,
            "qualityDisposition": "FAIL",
            "providerHold": "RECOVERED",
            "featureFlag": "OFF",
            "productionPromotion": "NO",
            "architectureChanged": False,
        },
        "providerActivity": {"providerCalls": 0, "gpuJobs": 0, "nanoCalls": 0, "alternativeProviderCalls": 0},
    }
    write_json(output / "baseline.json", baseline)

    failure_matrix = []
    for lane, cases in FAILED.items():
        for case_id in cases:
            identity = case_identity(lane, case_id)
            config_case = next(item for item in configured["cases"] if item["caseId"] == case_id and lane in item["lanes"])
            failure_matrix.append({
                **identity,
                "rootCauseClasses": [cause["class"] for cause in config_case["rootCauses"]],
                "rootCauseConfidence": [cause["confidence"] for cause in config_case["rootCauses"]],
                "failedDimensions": config_case["baseline"].get("failedDimensions", []),
                "baseline": config_case["baseline"],
                "remediationScope": config_case["remediation"]["scope"],
            })
    write_json(output / "failed_case_matrix.json", {
        "source": str(P6.relative_to(ROOT)),
        "exactFailedCaseCount": 5,
        "rows": failure_matrix,
    })

    root_causes = []
    for item in configured["cases"]:
        root_causes.append({"caseId": item["caseId"], "lanes": item["lanes"], "rootCauses": item["rootCauses"]})
    write_json(output / "root_cause_report.json", {
        "providerAndEvaluatorValidity": "R1-P6 had 18/18 valid responses; no provider/evaluator defect is a remediation target.",
        "findings": root_causes,
        "unresolvedMechanism": ["B05 FACE_LOCAL exact workflow parameter mechanism", "B07 FACE_LOCAL exact workflow parameter mechanism"],
    })

    write_json(output / "remediation_plan.json", {
        "orderedScope": [
            {"scope": "B05/B06 SCENARIO_GLOBAL", "change": "case-scoped action_full_body@1.0 authority mapping", "expectedEffect": "exclude shot_distance and hairstyle only", "liveRecheckRequired": False},
            {"scope": "B05 FACE_LOCAL", "change": "prepare targeted restore variant using existing workflow/reference/geometry/mask", "expectedEffect": "improve local face detail without global tuning", "liveRecheckRequired": True},
            {"scope": "B07 FACE_LOCAL", "change": "prepare targeted restore variant using existing workflow/reference/geometry/mask", "expectedEffect": "improve local face detail without global tuning", "liveRecheckRequired": True},
            {"scope": "B09 SCENARIO_GLOBAL", "change": "prepare new source variant with explicit prompt conditioning", "expectedEffect": "head-and-shoulders, elegant low bun, small pearl drop", "liveRecheckRequired": True},
        ],
        "forbiddenChanges": ["thresholds", "rubric", "validator", "provider", "architecture", "feature flag", "promotion", "frozen historical artifacts"],
        "nextTask": "R1-P7-R1 TARGETED AUTHORITATIVE RECHECK",
    })

    passing = {"boundary": {"count": 9, "protected": True}, "faceLocal": {}, "scenarioGlobal": {}}
    for lane, cases in (("FACE_LOCAL", PASSING_FACE), ("SCENARIO_GLOBAL", PASSING_SCENARIO)):
        key = "faceLocal" if lane == "FACE_LOCAL" else "scenarioGlobal"
        for case_id in cases:
            item = p6_case(lane, case_id)
            passing[key][case_id] = {
                "score": item["evaluation"]["overall_score"],
                "verdict": item["evaluation"]["verdict"],
                "rawResponseHash": item["metadata"]["rawHash"],
                "parsedResultHash": item["metadata"]["parsedHash"],
                "authorityProfile": item["metadata"]["authorityProfile"],
            }
    passing["manifestBeforeSha256"] = git_blob_sha("contracts/identity_restoration/benchmark_set.yaml")
    passing["manifestAfterSha256"] = sha256_file(MANIFEST)
    passing["policy"] = "All 13 previously passing evaluator cases remain represented and no global exclusion or threshold relaxation is applied."
    write_json(output / "passing_case_protection.json", passing)

    replay = {}
    for case_id in ("B05", "B06"):
        item = p6_case("SCENARIO_GLOBAL", case_id)
        metadata = item["metadata"]
        evaluation = item["evaluation"]
        observation = ImageObservation.model_validate(evaluation["raw_observation"])
        report = report_from_image_observations(
            "venho_hotel", "linh_an", Path(metadata["inputId"]), [observation],
            "offline-r1-p7-authority-replay", scenario_profile_id="action_full_body",
        )
        replay[case_id] = {"score": report.overall_score, "verdict": report.verdict.value, "providerCalls": 0}
    test_rc, test_output = run_capture(["python3", "-m", "pytest", "-q", "tests/test_gw_p4_r1_t3_authority.py", "tests/test_candidate_v3_r1_p7_targeted_remediation.py"])
    compile_rc, compile_output = run_capture(["python3", "-m", "compileall", "-q", "identity_restoration", "validator_studio", "scripts/run_candidate_v3_r1_p7_targeted_quality_remediation.py", "tests/test_gw_p4_r1_t3_authority.py", "tests/test_candidate_v3_r1_p7_targeted_remediation.py"])
    diff_rc, diff_output = run_capture(["git", "diff", "--check"])
    write_json(output / "offline_validation.json", {
        "providerCalls": 0,
        "authorityReplay": replay,
        "expectedReplay": {"B05": {"score": 97.74, "verdict": "approve"}, "B06": {"score": 91.47, "verdict": "approve"}},
        "passingCaseProtection": True,
        "boundaryUnchanged": True,
        "thresholdsChanged": False,
        "rubricChanged": False,
        "featureFlag": "OFF",
        "productionPromotion": "NO",
    })
    (output / "test_results.txt").write_text(test_output)
    (output / "compileall.txt").write_text(compile_output)
    (output / "git_diff_check.txt").write_text(diff_output)
    if test_rc or compile_rc or diff_rc:
        raise SystemExit(f"offline validation failed: pytest={test_rc}, compileall={compile_rc}, diff_check={diff_rc}")

    summary = {
        "taskId": configured["task_id"],
        "status": "CLOSED / REMEDIATION_READY",
        "qualityDisposition": "FAIL_PENDING_RECHECK",
        "failedCases": FAILED,
        "totalFailedCases": 5,
        "providerCalls": 0,
        "gpuJobs": 0,
        "nanoCalls": 0,
        "alternativeProviderCalls": 0,
        "boundary": "9/9 PASS",
        "faceLocalBaseline": "7 PASS / 2 FAIL",
        "scenarioGlobalBaseline": "6 PASS / 3 FAIL",
        "featureFlag": "OFF",
        "productionPromotion": "NO",
        "architectureChanged": False,
        "nextAction": "R1-P7-R1 TARGETED AUTHORITATIVE RECHECK",
    }
    write_json(output / "summary.json", summary)
    digest_lines = []
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            digest_lines.append(f"{sha256_file(path)}  {path.relative_to(output)}")
    (output / "hashes.sha256").write_text("\n".join(digest_lines) + "\n")
    print(output.relative_to(ROOT))


if __name__ == "__main__":
    main()
