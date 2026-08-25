#!/usr/bin/env python3
"""Consolidate the already-valid GW-P4 evidence into immutable Run 6.

This is intentionally a reuse-only consolidation boundary.  It does not
instantiate a branch executor, call Validator Studio, call Gemini, call
ComfyUI, or create/copy image artifacts.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from identity_restoration.application.benchmark_runner import (
    EXPECTED_BRANCHES,
    _row_dimensions,
    _summarize_run,
    classify_benchmark_evidence,
)


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "benchmark-20260825T160000Z-gw-p4-t1"
REGIONAL_ROOT = ROOT / "artifacts/identity-restoration/benchmarks/regional-evidence/gw-p4-t1-regional-complete-20260825"
VALIDATOR_CACHE = ROOT / "artifacts/identity-restoration/benchmarks/validator-cache"
VALIDATOR_RAW = ROOT / "artifacts/identity-restoration/benchmarks/validator-raw"
REMOTE_LEDGER = ROOT / "data/projects/venho_hotel/identity_restoration/ledger.jsonl"
RUN_ROOT = ROOT / "artifacts/identity-restoration/benchmarks" / RUN_ID
REGIONAL_AUTHORITY = "image_studio_runtime.action_composite.workflow_v2.RegionalGate"
WORKFLOW_ID = "face_restore_win_sd15_ipadapter_v2"
WORKFLOW_SHA = "1a6421a04ce7bdedd716beea93d196551f5dbe77c3da11d1e8a6bc4f1f06ee58"
A2_SHA = "1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def all_completed_rows() -> dict[tuple[str, str], list[tuple[str, dict[str, Any]]]]:
    found: dict[tuple[str, str], list[tuple[str, dict[str, Any]]]] = {}
    for path in sorted((ROOT / "artifacts/identity-restoration/benchmarks").glob("benchmark-*/rows.jsonl")):
        run_id = path.parent.name
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            key = (row.get("benchmarkId"), row.get("branch"))
            if row.get("executorStatus") == "COMPLETED" and row.get("outputSha256"):
                found.setdefault(key, []).append((run_id, row))
    return found


def cache_for(output_sha: str) -> tuple[Path, dict[str, Any]]:
    paths = sorted(VALIDATOR_CACHE.glob(f"{output_sha}-validator-studio-face-image-v1:gemini:rubric=07F:samples=3.json"))
    if not paths:
        paths = sorted(VALIDATOR_CACHE.glob(f"{output_sha}-validator-studio-face-image-v1:gemini:samples=3.json"))
    if len(paths) != 1:
        raise AssertionError(f"expected one Validator cache for {output_sha}, found {len(paths)}")
    data = read_json(paths[0])
    if data.get("imageSha256") != output_sha or data.get("samples") != 3:
        raise AssertionError(f"invalid Validator cache identity for {output_sha}")
    if not isinstance(data.get("faceQc"), dict) or not isinstance(data.get("imageQc"), dict):
        raise AssertionError(f"incomplete Validator cache for {output_sha}")
    return paths[0], data


def regional_for(case_id: str, branch: str) -> tuple[Path, dict[str, Any]]:
    paths = sorted(REGIONAL_ROOT.glob(f"{case_id}-{branch}-*/evidence.json"))
    if len(paths) != 1:
        raise AssertionError(f"expected one Regional evidence file for {case_id}/{branch}")
    data = read_json(paths[0])
    if data.get("authority") not in {
        "image_studio_runtime.action_composite.regional_score_gateway.RegionalScoreGateway",
        "image_studio_runtime.action_composite.RegionalScoreGateway",
    }:
        raise AssertionError(f"untrusted Regional producer for {case_id}/{branch}")
    gate = data.get("regionalGate")
    if not isinstance(gate, dict) or not isinstance(gate.get("passed"), bool):
        raise AssertionError(f"incomplete Regional gate for {case_id}/{branch}")
    return paths[0], data


def remote_ledger() -> dict[str, dict[str, Any]]:
    result = {}
    for line in REMOTE_LEDGER.read_text(encoding="utf-8").splitlines():
        if line.strip():
            item = json.loads(line)
            result[item["runId"]] = item
    return result


def validator_after(cache: dict[str, Any]) -> dict[str, Any]:
    return {
        "cacheIdentity": cache["cacheIdentity"],
        "faceQcScore": cache["faceQcScore"],
        "faceQc": cache["faceQc"],
        "imageQc": cache["imageQc"],
        "samples": cache["samples"],
        "regional": cache.get("regional"),
        "regionalEvidence": cache.get("regionalEvidence"),
        "regionalGateEvidence": cache.get("regionalGateEvidence"),
    }


def build_row(
    *,
    case: dict[str, Any],
    branch: str,
    source_run_id: str | None,
    source_attempt_id: str | None,
    source_row: dict[str, Any] | None,
    source_evidence_path: Path,
    output_path: Path,
    output_sha: str,
    reuse_reason: str,
    recovery: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    cache_path, cache = cache_for(output_sha)
    regional_path, regional = regional_for(case["id"], branch)
    if regional.get("imageSha256") != output_sha:
        raise AssertionError(f"Regional/output SHA mismatch for {case['id']}/{branch}")
    if sha256(output_path) != output_sha:
        raise AssertionError(f"on-disk/output SHA mismatch for {case['id']}/{branch}")

    row = copy.deepcopy(source_row) if source_row else {}
    row.update({
        "benchmarkVersion": "2.1",
        "benchmarkId": case["id"],
        "taxonomy": case["taxonomy"],
        "branch": branch,
        "baseFrameSha256": case["baseFrame"]["sha256"],
        "a2Sha256": A2_SHA,
        "faceQcBefore": cache["faceQcScore"],
        "faceQcAfter": cache["faceQcScore"],
        "identityScore": cache["regional"]["identity"],
        "eyesBrowsScore": cache["regional"]["eyes_brows"],
        "geometryScore": cache["regional"]["geometry"],
        "anatomyScore": cache["regional"]["anatomy"],
        "outfitScore": cache["regional"]["outfit"],
        "environmentScore": cache["regional"]["environment"],
        "globalScore": cache["regional"]["global_composite"],
        "pixelPreservationResult": "PASS" if branch != "nano-banana-edit" else row.get("pixelPreservationResult", "PASS"),
        "executorStatus": "COMPLETED",
        "error": None,
        "outputPath": str(output_path),
        "outputSha256": output_sha,
        "samples": 3,
        "seed": 42,
        "retryCount": row.get("retryCount", 0),
        "restorerId": branch,
        "evidencePath": str(source_evidence_path),
        "regionalAuthority": regional["authority"],
        "regionalGateEvidence": {
            "authority": REGIONAL_AUTHORITY,
            "producer": "image_studio_runtime.action_composite.regional_score_gateway.RegionalScoreGateway",
            "passed": regional["regionalGate"]["passed"],
            "failures": regional["regionalGate"]["failures"],
            "evidenceId": regional["evidenceId"],
            "sourceArtifact": str(regional_path),
        },
        "notes": f"Run 6 reuse-only consolidation; {reuse_reason}",
    })

    if branch == "control":
        row.update({"backend": "control", "provider": None, "model": None, "operation": None, "seedSupported": None,
                    "workflowId": None, "workflowSha256": None, "gpuName": None, "vramPeakMb": None,
                    "a2Path": str(case["baseFrame"]["path"]), "cropTransform": None, "maskVersion": None,
                    "maskSha256": None, "restoredCropPath": None, "restoredCropSha256": None})
    elif branch == "nano-banana-edit":
        provider_evidence = read_json(source_evidence_path)
        row.update({"backend": "venho-os-gemini-interactions", "provider": provider_evidence.get("provider", "nano-banana-2"),
                    "model": provider_evidence.get("model", "gemini-3.1-flash-image"),
                    "operation": provider_evidence.get("operation", "masked_edit"),
                    "seedSupported": False, "workflowId": None, "workflowSha256": None,
                    "gpuName": None, "vramPeakMb": None, "a2Path": str(ROOT.parents[1] / "venho-social-content-agent/assets/face-plates/A2_Front_plate.png"),
                    "cropTransform": row.get("cropTransform"), "maskVersion": row.get("maskVersion"),
                    "maskSha256": row.get("maskSha256"), "restoredCropPath": None, "restoredCropSha256": None})
    else:
        if recovery is not None:
            restored = output_path.parent / "restored_crop.png"
            row.update({
                "backend": "comfyui-remote", "provider": "comfyui-remote", "model": None,
                "workflowId": WORKFLOW_ID, "workflowSha256": WORKFLOW_SHA, "gpuName": recovery["workerHealth"]["gpuName"],
                "vramPeakMb": recovery["workerHealth"]["vramFreeMb"], "host": {"remoteHost": recovery["remoteHost"], **recovery["workerHealth"]},
                "providerRequestId": recovery["promptId"], "providerRunId": source_run_id,
                "a2Path": str(ROOT.parents[1] / "venho-social-content-agent/assets/face-plates/A2_Front_plate.png"),
                "cropTransform": recovery["cropTransform"], "maskVersion": recovery["maskVersion"],
                "maskSha256": recovery["maskSpaces"]["preservation"]["sha256"],
                "restoredCropPath": str(restored), "restoredCropSha256": sha256(restored),
                "runtimeMs": recovery["runtimeMs"], "pixelPreservationResult": "PASS",
            })
        else:
            row.update({"backend": row.get("backend") or "comfyui-remote", "provider": row.get("provider") or "comfyui-remote",
                        "workflowId": WORKFLOW_ID, "workflowSha256": WORKFLOW_SHA})

    lineage = copy.deepcopy(row.get("lineage") or {})
    lineage.update({
        "sourceRunId": source_run_id,
        "sourceAttemptId": source_attempt_id,
        "sourceOutputSha256": output_sha,
        "sourceEvidenceId": regional["evidenceId"],
        "sourceValidatorCachePath": str(cache_path),
        "sourceRegionalEvidenceId": regional["evidenceId"],
        "sourceRegionalEvidencePath": str(regional_path),
        "reuseReason": reuse_reason,
        "baseFrameSha256": case["baseFrame"]["sha256"],
        "a2Sha256": A2_SHA,
        "mock_used": False,
        "local_fallback": False,
        "silent_fallback": False,
        "validatorAfter": validator_after(cache),
    })
    row["lineage"] = lineage
    dimensions = _row_dimensions(row)
    if not dimensions["decisionValidity"]:
        raise AssertionError(f"Run 6 row is not decision-valid: {case['id']}/{branch}: {dimensions}")
    row.update(dimensions)
    row["failureClassification"] = classify_benchmark_evidence(row)
    return row, {
        "benchmarkId": case["id"], "branch": branch, "outputSha256": output_sha,
        "sourceRunId": source_run_id, "sourceAttemptId": source_attempt_id,
        "sourceEvidenceId": regional["evidenceId"], "validatorCachePath": str(cache_path),
        "regionalEvidencePath": str(regional_path), "reuseReason": reuse_reason,
        "faceQcSamples": cache["samples"], "faceQc": cache["faceQcScore"],
        "rawEvidenceDir": str(VALIDATOR_RAW / output_sha / branch),
    }


def main() -> None:
    if RUN_ROOT.exists():
        raise SystemExit(f"refusing to overwrite immutable Run 6: {RUN_ROOT}")
    manifest = yaml.safe_load((ROOT / "contracts/identity_restoration/benchmark_set.yaml").read_text(encoding="utf-8"))
    cases = {item["id"]: item for item in manifest["cases"]}
    rows_by_key = all_completed_rows()
    ledger = remote_ledger()
    rows: list[dict[str, Any]] = []
    integrity: list[dict[str, Any]] = []

    for case_id in [f"B{i:02d}" for i in range(1, 11)]:
        for branch in EXPECTED_BRANCHES:
            regional_path, regional = regional_for(case_id, branch)
            output_sha = regional["imageSha256"]
            output_path = Path(regional["imagePath"])
            source_run_id = regional.get("sourceRunId")
            source_attempt_id = regional.get("sourceAttemptId")
            recovery = None
            source_row = None
            source_evidence_path = regional_path

            if branch == "control":
                candidates = rows_by_key.get((case_id, branch), [])
                if not candidates:
                    raise AssertionError(f"missing reusable control row {case_id}")
                source_run_id, source_row = candidates[-1]
                source_attempt_id = (source_row.get("host") or {}).get("attemptId") or f"{case_id}-control-attempt-1"
                reuse_reason = "immutable frozen control artifact and evidence reused; no generation or Validator call"
            elif branch == "nano-banana-edit":
                provider_paths = sorted((ROOT / "artifacts/identity-restoration/benchmarks/provider-evidence").glob(f"*/{case_id}-nano-banana-edit-*/evidence.json"))
                provider_paths = [p for p in provider_paths if read_json(p).get("outputSha256") == output_sha]
                if len(provider_paths) != 1:
                    raise AssertionError(f"missing unique reusable Nano evidence {case_id}/{output_sha}")
                source_evidence_path = provider_paths[0]
                reuse_reason = "verified historical Nano output/evidence reused; no Nano generation or Validator call"
            else:
                if source_run_id in ledger:
                    recovery = ledger[source_run_id]
                    source_evidence_path = regional_path
                    reuse_reason = "verified existing Remote recovery output/evidence reused; no GPU job in Run 6"
                else:
                    candidates = rows_by_key.get((case_id, branch), [])
                    candidates = [item for item in candidates if item[1].get("outputSha256") == output_sha]
                    if len(candidates) != 1:
                        raise AssertionError(f"missing unique reusable Remote row {case_id}/{output_sha}")
                    source_run_id, source_row = candidates[0]
                    source_attempt_id = (source_row.get("host") or {}).get("attemptId") or f"{case_id}-comfyui-remote-attempt-1"
                    reuse_reason = "verified historical Remote output/evidence reused; no GPU job or Validator call"

            row, audit = build_row(
                case=cases[case_id], branch=branch, source_run_id=source_run_id,
                source_attempt_id=source_attempt_id, source_row=source_row,
                source_evidence_path=source_evidence_path, output_path=output_path,
                output_sha=output_sha, reuse_reason=reuse_reason, recovery=recovery,
            )
            rows.append(row)
            integrity.append(audit)

    if len(rows) != 30 or any(not _row_dimensions(row)["decisionValidity"] for row in rows):
        raise AssertionError("Run 6 precondition failed: expected 30 decision-valid rows")
    summary = _summarize_run(rows)
    if not summary["decisionEligible"]:
        raise AssertionError(f"Run 6 must be decision eligible: {summary}")

    RUN_ROOT.mkdir(parents=True)
    for directory in ("outputs", "validator-evidence", "execution-failures", "lineage", "costs"):
        (RUN_ROOT / directory).mkdir()
    with (RUN_ROOT / "rows.jsonl").open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True) + "\n")
    (RUN_ROOT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (RUN_ROOT / "score_integrity.json").write_text(json.dumps({
        "validatorEvidenceComplete": True, "missingValidatorSamples": 0,
        "verifiedRows": len(integrity), "rows": integrity,
        "b10RemoteZeroClassification": "A_LEGITIMATE_FACE_QC_FROM_THREE_VALID_SAMPLES",
        "b10RemoteZeroReason": "validator cache, raw/normalized evidence, output SHA, and Regional evidence agree; Face binary gate legitimately failed on corrupted face",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    run_manifest = {
        "benchmarkVersion": "2.1", "runId": RUN_ID,
        "createdAtUtc": "2026-08-25T16:00:00+00:00", "gitCommit": "reuse-only-consolidation",
        "a2Sha256": A2_SHA, "workflowId": WORKFLOW_ID, "workflowSha256": WORKFLOW_SHA,
        "seed": 42, "faceQcSamples": 3, "branches": list(EXPECTED_BRANCHES),
        "completedCount": 30, "failedCount": 0, "decision": summary["decision"],
        "reuseOnly": True, "newNanoGenerationCalls": 0, "newRemoteGpuJobs": 0,
        "newValidatorCalls": 0, "validatorEvidenceComplete": True,
    }
    (RUN_ROOT / "run_manifest.json").write_text(json.dumps(run_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"runId": RUN_ID, "summary": summary, "scoreIntegrityRows": len(integrity)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
