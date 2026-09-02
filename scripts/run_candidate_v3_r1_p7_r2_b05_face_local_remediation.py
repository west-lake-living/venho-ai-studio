"""Prepare the offline, B05-only R1-P7-R2 remediation evidence bundle."""

from __future__ import annotations

import hashlib
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
P6 = PHASE7 / "r1-p6-authoritative-evaluation-resume-20260902T024012Z"
P7 = PHASE7 / "r1-p7-targeted-quality-remediation-20260902T030000Z"
R1 = PHASE7 / "r1-p7-r1-targeted-authoritative-recheck-20260902T032200Z"
CONFIG = ROOT / "config/projects/venho_hotel/identity_restoration/r1_p7_r2_b05_face_local.yaml"
OUT = Path(os.environ.get(
    "R1_P7_R2_OUTPUT_DIR",
    str(PHASE7 / ("r1-p7-r2-b05-face-local-remediation-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))),
))
TASK_ID = "R1-P7-R2-TARGETED-REMEDIATION-B05-FACE-LOCAL"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha(path: Path) -> str:
    return sha(path.read_bytes())


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def run_offline(command: list[str]) -> tuple[int, str]:
    env = dict(os.environ)
    env.pop("VALIDATOR_LIVE_ENABLED", None)
    env.pop("GEMINI_API_KEY", None)
    env.pop("GOOGLE_API_KEY", None)
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, check=False)
    return result.returncode, (result.stdout + result.stderr).rstrip() + "\n"


def p6_metadata(case_id: str) -> dict[str, Any]:
    return load_json(P6 / "face_local" / f"case-{int(case_id[1:]):02d}" / "request_metadata.json")


def p6_report(case_id: str) -> dict[str, Any]:
    return load_json(P6 / "face_local" / f"case-{int(case_id[1:]):02d}" / "evaluation_report.json")


def r1_metadata(case_id: str) -> dict[str, Any]:
    return load_json(R1 / "face_local" / case_id / "request_metadata.json")


def r1_report(case_id: str) -> dict[str, Any]:
    return load_json(R1 / "face_local" / case_id / "evaluation_report.json")


def geometry(case_id: str) -> dict[str, Any]:
    return load_json(ROOT / f"artifacts/identity-restoration/benchmark-geometry/v2.1/{case_id}/geometry_manifest.json")


def job(case_id: str) -> dict[str, Any]:
    number = int(case_id[1:])
    run = "phase7-benchmark-20260828" if number <= 4 or number >= 7 else "phase7-diagnostic-20260828"
    return load_json(PHASE7 / "jobs" / f"{run}-{case_id}.json")


def finish_hashes() -> None:
    files = {
        str(path.relative_to(OUT)): file_sha(path)
        for path in sorted(OUT.rglob("*"))
        if path.is_file() and path.name != "hashes.sha256"
    }
    write_json(OUT / "hashes.sha256", {"algorithm": "SHA-256", "files": files, "count": len(files)})


def main() -> int:
    if os.environ.get("TARGETED_REMEDIATION_R2_AUTHORIZED") != "TRUE":
        raise SystemExit("TARGETED_REMEDIATION_R2_AUTHORIZED must be TRUE")
    if os.environ.get("B05_FACE_LOCAL_RECHECK_AUTHORIZED", "FALSE") == "TRUE":
        raise SystemExit("R1-P7-R2 is remediation-only; B05_FACE_LOCAL_RECHECK_AUTHORIZED must be FALSE")
    if OUT.exists() and any(OUT.iterdir()):
        raise SystemExit(f"refusing to overwrite evidence directory: {OUT}")
    OUT.mkdir(parents=True, exist_ok=True)
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    old = p6_report("B05")
    current = r1_report("B05")
    write_json(OUT / "baseline.json", {
        "taskId": TASK_ID,
        "authorization": config["authorization"],
        "sourceEvidence": {"p6": str(P6.relative_to(ROOT)), "p7": str(P7.relative_to(ROOT)), "p7R1": str(R1.relative_to(ROOT))},
        "startState": {"r1P7R1": "CLOSED / PASS", "boundary": "9/9 PASS", "faceLocal": "8/9 PASS", "scenarioGlobal": "9/9 PASS", "pending": 0, "qualityDisposition": "FAIL", "remainingFailure": "B05 / FACE_LOCAL", "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False},
        "p6B05": {"score": old["overall_score"], "verdict": old["verdict"], "metadata": p6_metadata("B05")},
        "r1B05": {"score": current["overall_score"], "verdict": current["verdict"], "metadata": r1_metadata("B05")},
    })

    dimensions = {}
    for key, value in current["category_scores"].items():
        dimensions[key] = {"measuredResult": value, "thresholdExpectation": 90.0, "deltaToPass": round(value - 90.0, 2), "status": "PASS" if value >= 90.0 else "FAIL"}
    write_json(OUT / "b05_failure_reconstruction.json", {
        "caseId": "B05", "evaluator": "FACE_LOCAL", "score": current["overall_score"], "verdict": current["verdict"],
        "provider": r1_metadata("B05")["provider"], "model": r1_metadata("B05")["model"],
        "validResponse": r1_metadata("B05")["validResponse"], "lineage": r1_metadata("B05")["lineage"],
        "inputId": r1_metadata("B05")["inputId"], "inputSha256": r1_metadata("B05")["inputSha256"],
        "rawHash": r1_metadata("B05")["rawHash"], "parsedHash": r1_metadata("B05")["parsedHash"],
        "dimensions": dimensions,
        "providerCalls": 0,
    })

    b05g = geometry("B05")
    b07g = geometry("B07")
    write_json(OUT / "b05_dimension_analysis.json", {
        "threshold": 90.0,
        "failedDimensions": {key: value for key, value in dimensions.items() if value["status"] == "FAIL"},
        "passingDimensions": {key: value for key, value in dimensions.items() if value["status"] == "PASS"},
        "geometryEvidence": {
            "B05": {"faceScale": b05g["geometry"]["face_scale"], "yaw": b05g["geometry"]["yaw"], "faceBboxPixels": [b05g["geometry"]["face_bbox"]["right"] - b05g["geometry"]["face_bbox"]["left"], b05g["geometry"]["face_bbox"]["bottom"] - b05g["geometry"]["face_bbox"]["top"]], "cropSize": b05g["cropSize"], "geometrySha256": file_sha(ROOT / "artifacts/identity-restoration/benchmark-geometry/v2.1/B05/geometry_manifest.json")},
            "B07": {"faceScale": b07g["geometry"]["face_scale"], "yaw": b07g["geometry"]["yaw"], "faceBboxPixels": [b07g["geometry"]["face_bbox"]["right"] - b07g["geometry"]["face_bbox"]["left"], b07g["geometry"]["face_bbox"]["bottom"] - b07g["geometry"]["face_bbox"]["top"]], "cropSize": b07g["cropSize"], "geometrySha256": file_sha(ROOT / "artifacts/identity-restoration/benchmark-geometry/v2.1/B07/geometry_manifest.json")},
        },
        "interpretation": "B05 has the smallest face and most extreme yaw among the closest face-local controls; this is a measured difficulty condition, not evidence that the geometry extractor or mask is defective.",
    })

    peer_rows = []
    for cid in ["B01", "B02", "B03", "B04", "B06", "B07", "B08", "B09"]:
        number = int(cid[1:])
        peer = p6_report(cid)
        g = geometry(cid)
        a = job(cid)["lineage"]["bridge"]["adapterEvidence"]
        peer_rows.append({"caseId": cid, "score": peer["overall_score"], "verdict": peer["verdict"], "workflowId": a["workflowId"], "workflowSha256": a["workflowSha256"], "effectiveConfigSha256": a["boundConfig"]["effectiveConfigSha256"], "faceScale": g["geometry"]["face_scale"], "yaw": g["geometry"]["yaw"], "authorityProfile": p6_metadata(cid)["authorityProfile"]})
    write_json(OUT / "passing_peer_comparison.json", {
        "target": {"caseId": "B05", "score": current["overall_score"], "verdict": current["verdict"], "workflowId": job("B05")["lineage"]["bridge"]["adapterEvidence"]["workflowId"], "workflowSha256": job("B05")["lineage"]["bridge"]["adapterEvidence"]["workflowSha256"], "effectiveConfigSha256": job("B05")["lineage"]["bridge"]["adapterEvidence"]["boundConfig"]["effectiveConfigSha256"], "faceScale": b05g["geometry"]["face_scale"], "yaw": b05g["geometry"]["yaw"], "authorityProfile": r1_metadata("B05")["authorityProfile"]},
        "closestControl": {"caseId": "B07", "score": r1_report("B07")["overall_score"], "verdict": r1_report("B07")["verdict"], "workflowId": job("B07")["lineage"]["bridge"]["adapterEvidence"]["workflowId"], "workflowSha256": job("B07")["lineage"]["bridge"]["adapterEvidence"]["workflowSha256"], "effectiveConfigSha256": job("B07")["lineage"]["bridge"]["adapterEvidence"]["boundConfig"]["effectiveConfigSha256"], "faceScale": b07g["geometry"]["face_scale"], "yaw": b07g["geometry"]["yaw"], "authorityProfile": r1_metadata("B07")["authorityProfile"]},
        "sameWorkflowPassingPeers": peer_rows,
        "scenarioControl": {"caseId": "B05", "score": load_json(R1 / "scenario_global" / "B05" / "evaluation_report.json")["overall_score"], "verdict": load_json(R1 / "scenario_global" / "B05" / "evaluation_report.json")["verdict"], "profile": "action_full_body"},
        "keyDifference": "The workflow, A2 reference, effective config, authority, and validator path are not a B05-only defect; B05 is uniquely small-face/extreme-side-pose, and its residual failure is local face detail rather than scenario/global quality.",
    })

    write_json(OUT / "root_cause_report.json", {
        "caseId": "B05", "rootCause": "TRUE_LOCAL_FACE_QUALITY_FAILURE / FACE_DETAIL_FAILURE",
        "rootCauseConfidence": "HIGH_FOR_FAILURE_CLASS_MEDIUM_FOR_GEOMETRY_MECHANISM",
        "causalEvidence": [
            "R1-P7-R1 returned valid provider, schema, DTO, and lineage evidence; only eyes_and_brows, facial_shape, and mouth_and_chin remain below 90.",
            "The same frozen B05 input remains 88.50/revise after R1-P7-R1; B05 SCENARIO_GLOBAL is 93.79/approve.",
            "B05 uses the same v3 workflow, A2 reference, effective config, and canonical validator path as passing peers.",
            "B05 geometry is valid but has face scale 0.072265625 and yaw -49.077 degrees, versus B07 face scale 0.1103515625 and yaw 9.6109 degrees.",
        ],
        "notProven": ["specific provider-side denoise/CFG/strength parameter", "geometry extractor defect", "mask defect", "reference binding defect"],
        "decision": "Do not invent a parameter change offline; prepare one B05-only restore variant and defer its single authoritative recheck.",
    })
    write_json(OUT / "remediation_plan.json", {
        "caseId": "B05", "rootCause": "TRUE_LOCAL_FACE_QUALITY_FAILURE / FACE_DETAIL_FAILURE",
        "filesAndConfigs": [str(CONFIG.relative_to(ROOT))],
        "change": "Bind a new B05-only targeted restore variant request to the existing v3 workflow, preserving the frozen source, geometry, crop, masks, A2 reference, rubric, and thresholds.",
        "expectedFaceLocalEffect": "Improve B05 side-pose local facial detail; prove only by the next one-call authoritative recheck.",
        "expectedScenarioGlobalEffect": "No change; B05 SCENARIO_GLOBAL remains protected at 93.79/approve.",
        "passingCasesAtRisk": "None by scope; B07 and all other passing paths are not rerun or reclassified.",
        "regressionProtection": ["B05_ONLY", "no global parameter tuning", "no threshold/rubric change", "no provider switch", "no frozen artifact mutation"],
        "liveRecheckRequired": True,
        "nextAction": "R1-P7-R2-R1 B05 FACE_LOCAL AUTHORITATIVE RECHECK",
    })

    p7r1_summary = load_json(R1 / "targeted_recheck_summary.json")
    write_json(OUT / "passing_case_protection.json", {
        "baseline": {"boundary": "9/9 PASS", "faceLocal": "8/9 PASS", "scenarioGlobal": "9/9 PASS"},
        "protectedCases": {"boundary": 9, "faceLocalPassing": ["B01", "B02", "B03", "B04", "B06", "B07", "B08", "B09"], "scenarioGlobalPassing": ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B09"]},
        "protectedHashes": {"r1P7R1SummarySha256": file_sha(R1 / "targeted_recheck_summary.json"), "a2Sha256": "1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d", "faceRubricSha256": file_sha(ROOT / "config/projects/venho_hotel/face_qc_rubric.yaml"), "qualityPolicySha256": file_sha(ROOT / "identity_restoration/config/candidate_v3_quality_policy_v1.json")},
        "r1P7R1TargetedResults": {"B05": p7r1_summary["faceLocal"]["results"][0], "B07": p7r1_summary["faceLocal"]["results"][1]},
        "status": "PASSING_BASELINE_PROTECTED",
    })

    test_files = ["tests/test_candidate_v3_r1_p7_r2_b05_face_local.py", "tests/test_candidate_v3_r1_p7_r1_targeted_recheck.py", "tests/test_candidate_v3_r1_p7_targeted_remediation.py", "tests/test_gw_p4_r1_t3_authority.py", "tests/test_candidate_v3_r1_p5_provider_recovery_gate.py", "tests/identity_restoration/application/test_phase7_candidate_v3_evaluation.py", "tests/identity_restoration/application/test_benchmark_orchestration.py", "tests/identity_restoration/contracts/test_candidate_v3_schemas.py"]
    test_code, test_output = run_offline(["python3", "-m", "pytest", "-q", *test_files])
    compile_code, compile_output = run_offline(["python3", "-m", "compileall", "-q", "identity_restoration", "validator_studio", "shared/vision", "scripts/run_candidate_v3_r1_p7_r2_b05_face_local_remediation.py"])
    diff_code, diff_output = run_offline(["git", "diff", "--check"])
    (OUT / "test_results.txt").write_text(test_output, encoding="utf-8")
    (OUT / "compileall.txt").write_text(compile_output if compile_output.strip() else "compileall=PASS\n", encoding="utf-8")
    (OUT / "git_diff_check.txt").write_text(diff_output if diff_output.strip() else "git_diff_check=PASS\n", encoding="utf-8")
    preflight_status = "PASS" if test_code == compile_code == diff_code == 0 else "BLOCKED_LOCAL_REGRESSION"
    write_json(OUT / "offline_validation.json", {"status": preflight_status, "providerCalls": 0, "retries": 0, "testsExitCode": test_code, "compileallExitCode": compile_code, "gitDiffCheckExitCode": diff_code, "scopedBindings": {"B05": "B05_ONLY", "B07": "unchanged", "scenarioGlobal": "unchanged"}, "thresholdsChanged": False, "rubricChanged": False, "providerGateChanged": False, "unknownAuthorityFailClosed": True, "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False})
    write_json(OUT / "summary.json", {"taskId": TASK_ID, "status": "CLOSED / REMEDIATION_READY" if preflight_status == "PASS" else "BLOCKED / LOCAL_REGRESSION", "qualityDisposition": "FAIL_PENDING_B05_RECHECK" if preflight_status == "PASS" else "FAIL", "remainingFailure": "B05 / FACE_LOCAL", "baseline": {"boundary": "9/9 PASS", "faceLocal": "8/9 PASS", "scenarioGlobal": "9/9 PASS"}, "providerCalls": 0, "gpuJobs": 0, "nanoCalls": 0, "alternativeProviderCalls": 0, "nextAction": "R1-P7-R2-R1 B05 FACE_LOCAL AUTHORITATIVE RECHECK", "requiresSeparateAuthorization": True})
    finish_hashes()
    print(OUT.resolve().relative_to(ROOT))
    return 0 if preflight_status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
