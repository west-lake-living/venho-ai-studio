#!/usr/bin/env python3
"""Complete the B05 artifact contract, stopping if remediation is unresolved."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
PHASE7 = ROOT / "artifacts/identity-restoration/phase7-candidate-v3"
P6 = PHASE7 / "r1-p6-authoritative-evaluation-resume-20260902T024012Z"
P7 = PHASE7 / "r1-p7-targeted-quality-remediation-20260902T030000Z"
R2 = PHASE7 / "r1-p7-r2-b05-face-local-remediation-20260902T033100Z"
R2_R1 = PHASE7 / "r1-p7-r2-r1-b05-face-local-recheck-20260902T033242Z"
P8 = PHASE7 / "r1-p8-b05-recovery-final-closure-20260902T033721Z"
JOB = PHASE7 / "jobs/phase7-diagnostic-20260828-B05.json"
GEOMETRY = PHASE7 / "../benchmark-geometry/v2.1/B05/geometry_manifest.json"
CONFIG = ROOT / "config/projects/venho_hotel/identity_restoration/r1_p7_r2_b05_face_local.yaml"
OUT = Path(os.environ.get(
    "R1_P9_OUTPUT_DIR",
    str(PHASE7 / ("r1-p9-b05-artifact-contract-final-closure-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))),
))
TASK_ID = "R1-P9-B05-ARTIFACT-CONTRACT-AND-FINAL-CLOSURE"


def sha_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def finish_hashes() -> None:
    files = {
        str(path.relative_to(OUT)): sha_path(path)
        for path in sorted(OUT.rglob("*"))
        if path.is_file() and path.name != "hashes.sha256"
    }
    write_json(OUT / "hashes.sha256", {"algorithm": "SHA-256", "files": files, "count": len(files)})


def authority_reconstruction(config: dict[str, Any], job: dict[str, Any], geometry: dict[str, Any], r1_metadata: dict[str, Any], r2_report: dict[str, Any]) -> dict[str, Any]:
    adapter = job["lineage"]["bridge"]["adapterEvidence"]
    transform = job["lineage"]["transform"]
    source = job["lineage"]["bridge"]
    return {
        "caseId": "B05",
        "rootCause": "TRUE_LOCAL_FACE_QUALITY_FAILURE / FACE_DETAIL_FAILURE",
        "approvedVariantId": config["remediation"]["variantId"],
        "approvedWorkflow": {"id": adapter["workflowId"], "sha256": adapter["workflowSha256"], "source": "B05 immutable job lineage"},
        "approvedReferenceBinding": {"referencePackId": job["identityPackId"], "a2Sha256": adapter["selectedReferenceHashes"][0], "source": "B05 immutable job lineage / approved A2"},
        "approvedPreservationRules": config["remediation"]["preserve"],
        "knownGeometry": {"faceScale": geometry["geometry"]["face_scale"], "yaw": geometry["geometry"]["yaw"], "cropSize": geometry["cropSize"], "source": "benchmark geometry v2.1"},
        "knownFaceLocalDefects": {"score": r2_report["score"], "verdict": r2_report["verdict"], "dimensions": r2_report["dimensions"], "source": "R1-P7-R1 valid FACE_LOCAL result"},
        "knownInputLineage": {"inputPath": r1_metadata["inputId"], "inputSha256": r1_metadata["inputSha256"], "sourceCase": source["candidateProfileId"], "source": "R1-P7-R1 request metadata"},
        "knownWorkflowParameters": {**adapter["boundConfig"], "canonicalTransformSha256": transform["transform"]["transformSha256"], "maskSha256": transform["canonicalEditableMaskSha256"], "source": "B05 immutable job lineage"},
        "missingFields": [
            "restore_parameters.remediation_change",
            "workflow_version",
            "source_manifest_for_new_variant",
            "output_artifact_id",
            "output_path",
            "output_manifest",
            "output_binding_hash",
        ],
        "unresolvedParameters": ["The R2 evidence identifies a face-detail variant intent but proves no concrete denoise/CFG/strength/seed or other restore delta."],
    }


def incomplete_contract(authority: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
    adapter = job["lineage"]["bridge"]["adapterEvidence"]
    return {
        "contractId": None,
        "caseId": "B05",
        "sourceArtifactId": job["jobId"],
        "sourceArtifactHash": job["lineage"]["transform"]["canonicalImageSha256"],
        "sourceManifest": None,
        "sourceLineage": authority["knownInputLineage"],
        "restoreVariantId": authority["approvedVariantId"],
        "workflowId": adapter["workflowId"],
        "workflowVersion": None,
        "workflowHash": adapter["workflowSha256"],
        "referencePackId": authority["approvedReferenceBinding"]["referencePackId"],
        "referenceBinding": authority["approvedReferenceBinding"],
        "authorityProfile": "action_full_body",
        "inputPath": authority["knownInputLineage"]["inputPath"],
        "outputPath": None,
        "outputArtifactId": None,
        "restoreParameters": {"baseline": authority["knownWorkflowParameters"], "remediationChange": None},
        "faceRegionAndMaskParameters": {"geometry": authority["knownGeometry"], "maskSha256": authority["knownWorkflowParameters"]["maskSha256"]},
        "canonicalTransform": {"transformSha256": authority["knownWorkflowParameters"]["canonicalTransformSha256"]},
        "preservationRules": authority["approvedPreservationRules"],
        "expectedOutputContract": {"required": ["artifact", "manifest", "lineage", "hashes"], "valid": False},
        "contractComplete": False,
        "unresolvedParameters": authority["unresolvedParameters"],
    }


def main() -> int:
    if OUT.exists() and any(OUT.iterdir()):
        raise SystemExit(f"refusing to overwrite evidence directory: {OUT}")
    OUT.mkdir(parents=True, exist_ok=True)
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    job = load_json(JOB)
    geometry = load_json(GEOMETRY)
    r1_metadata = load_json(R2 / "baseline.json")["r1B05"]["metadata"]
    r2_report = load_json(R2 / "b05_failure_reconstruction.json")
    r2_summary = load_json(R2 / "summary.json")
    r2r1_summary = load_json(R2_R1 / "summary.json")
    p8_summary = load_json(P8 / "summary.json")
    p7_summary = load_json(P7 / "summary.json")

    start_reasons: list[str] = []
    if os.environ.get("R1_P9_B05_ARTIFACT_CONTRACT_AND_CLOSURE_AUTHORIZED") != "TRUE":
        start_reasons.append("R1_P9_AUTHORIZATION_NOT_TRUE")
    if p8_summary.get("status") != "BLOCKED / REMEDIATION_CONTRACT_INCOMPLETE":
        start_reasons.append("R1_P8_START_STATE_MISMATCH")
    if r2_summary.get("status") != "CLOSED / REMEDIATION_READY":
        start_reasons.append("R1_P7_R2_START_STATE_MISMATCH")
    if r2r1_summary.get("status") != "BLOCKED_LOCAL_REGRESSION":
        start_reasons.append("R1_P7_R2_R1_START_STATE_MISMATCH")
    if p7_summary.get("status") != "CLOSED / REMEDIATION_READY":
        start_reasons.append("R1_P7_START_STATE_MISMATCH")

    authority = authority_reconstruction(config, job, geometry, r1_metadata, r2_report)
    contract = incomplete_contract(authority, job)
    t0_status = "PASS" if not start_reasons else "BLOCKED / START_STATE_MISMATCH"
    t1_status = "BLOCKED / REMEDIATION_PARAMETER_UNRESOLVED" if t0_status == "PASS" else "NOT_EXECUTED"
    write_json(OUT / "baseline.json", {"taskId": TASK_ID, "authorization": {"name": "R1_P9_B05_ARTIFACT_CONTRACT_AND_CLOSURE_AUTHORIZED", "requiredValue": "TRUE", "receivedValue": os.environ.get("R1_P9_B05_ARTIFACT_CONTRACT_AND_CLOSURE_AUTHORIZED")}, "startState": {"r1P8": p8_summary.get("status"), "r1P7R2": r2_summary.get("status"), "r1P7R2R1": r2r1_summary.get("status"), "blocker": "REMEDIATION_CONTRACT_INCOMPLETE", "boundary": "9/9 PASS", "faceLocal": "8/9 PASS", "scenarioGlobal": "9/9 PASS", "pending": 1, "qualityDisposition": "FAIL_PENDING_B05_RECHECK", "providerHold": "RECOVERED", "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False}, "startReasons": start_reasons})
    write_json(OUT / "t0-authority-reconstruction" / "result.json", {"status": t0_status, "knownAuthority": authority, "missingFields": authority["missingFields"], "sourceEvidence": {"p6": str(P6.relative_to(ROOT)), "p7": str(P7.relative_to(ROOT)), "r2": str(R2.relative_to(ROOT)), "r2R1": str(R2_R1.relative_to(ROOT)), "p8": str(P8.relative_to(ROOT))}})
    write_json(OUT / "artifact_contract_authority.json", authority)
    write_json(OUT / "artifact_contract.json", {**contract, "status": t1_status})

    focused_tests = [
        "tests/test_candidate_v3_r1_p9_b05_artifact_contract_final_closure.py",
        "tests/test_candidate_v3_r1_p8_b05_recovery_final_closure.py",
        "tests/test_candidate_v3_r1_p7_r2_r1_b05_face_local_recheck.py",
        "tests/test_candidate_v3_r1_p7_r2_b05_face_local.py",
        "tests/test_candidate_v3_r1_p7_r1_targeted_recheck.py",
        "tests/test_candidate_v3_r1_p7_targeted_remediation.py",
        "tests/test_candidate_v3_r1_p5_provider_recovery_gate.py",
        "tests/identity_restoration/application/test_phase7_candidate_v3_evaluation.py",
        "tests/identity_restoration/contracts/test_candidate_v3_schemas.py",
    ]
    test_code, test_output = run_offline(["python3", "-m", "pytest", "-q", *focused_tests])
    compile_code, compile_output = run_offline(["python3", "-m", "compileall", "-q", "identity_restoration", "validator_studio", "shared/vision", "scripts/run_candidate_v3_r1_p9_b05_artifact_contract_final_closure.py"])
    diff_code, diff_output = run_offline(["git", "diff", "--check"])
    (OUT / "test_results.txt").write_text(test_output, encoding="utf-8")
    (OUT / "compileall.txt").write_text(compile_output if compile_output.strip() else "compileall=PASS\n", encoding="utf-8")
    (OUT / "git_diff_check.txt").write_text(diff_output if diff_output.strip() else "git_diff_check=PASS\n", encoding="utf-8")

    final_status = t1_status if test_code == compile_code == diff_code == 0 else "BLOCKED / LOCAL_REGRESSION"
    write_json(OUT / "t1-artifact-contract" / "result.json", {"status": final_status, "contract": contract, "missingFields": authority["missingFields"], "unresolvedParameters": authority["unresolvedParameters"], "contractComplete": False, "reason": "Concrete remediation parameters are not proven by R2 evidence or repository-native deterministic rules."})
    write_json(OUT / "provider_call_accounting.json", {"maxProviderCalls": 1, "providerCalls": 0, "retries": 0, "gpuJobs": 0, "nanoCalls": 0, "alternativeProviderCalls": 0})
    write_json(OUT / "gpu_job_accounting.json", {"maxArtifacts": 1, "artifactsCreated": 0, "gpuJobs": 0, "status": "NOT_EXECUTED"})
    write_json(OUT / "before_after_comparison.json", {"caseId": "B05", "before": {"score": 88.50, "verdict": "revise", "eyesBrows": 87, "facialShape": 88, "mouthChin": 89}, "after": {"status": "NOT_EVALUATED", "score": None, "verdict": None}, "deltas": None})
    write_json(OUT / "quality_disposition.json", {"taskId": TASK_ID, "status": "BLOCKED / REMEDIATION_PARAMETER_UNRESOLVED", "boundary": "9/9 PASS", "faceLocal": "8/9 PASS", "scenarioGlobal": "9/9 PASS", "pendingAuthoritativeEvaluations": 1, "qualityDisposition": "FAIL_PENDING_B05_RECHECK", "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False, "nextAction": "COMPLETE_CONCRETE_B05_REMEDIATION_PARAMETER_CONTRACT"})
    write_json(OUT / "summary.json", {"taskId": TASK_ID, "status": "BLOCKED / REMEDIATION_PARAMETER_UNRESOLVED", "t0": t0_status, "t1": final_status, "t2": "NOT_EXECUTED", "t3": "NOT_EXECUTED", "t4": "NOT_EXECUTED", "t5": "NOT_EXECUTED", "t6": "NOT_EXECUTED", "providerCalls": 0, "retries": 0, "gpuJobs": 0, "nanoCalls": 0, "alternativeProviderCalls": 0, "boundary": "9/9 PASS", "faceLocal": "8/9 PASS", "scenarioGlobal": "9/9 PASS", "pendingAuthoritativeEvaluations": 1, "qualityDisposition": "FAIL_PENDING_B05_RECHECK", "featureFlag": "OFF", "productionPromotion": "NO", "architectureChanged": False, "nextAction": "COMPLETE_CONCRETE_B05_REMEDIATION_PARAMETER_CONTRACT", "blockers": authority["unresolvedParameters"] + start_reasons})
    finish_hashes()
    print(json.dumps({"status": "BLOCKED / REMEDIATION_PARAMETER_UNRESOLVED", "output": str(OUT), "providerCalls": 0, "missingFields": authority["missingFields"]}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
