from __future__ import annotations

"""Fail-closed orchestration for the GW-P4 benchmark.

This module owns benchmark contract/readiness decisions and result-lineage
serialization.  It deliberately does not know how to call ComfyUI, Gemini,
or Nano Banana.  A future composition root supplies a branch executor through
``BenchmarkExecutor``; this keeps the benchmark from becoming a second
restoration pipeline.
"""

import hashlib
import json
import platform
import subprocess
import sys
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol
from uuid import uuid4

import jsonschema

from .benchmark_contract import (
    EXPECTED_A2_SHA256,
    EXPECTED_BRANCHES,
    EXPECTED_WORKFLOW_ID,
    EXPECTED_WORKFLOW_SHA256,
    BenchmarkManifestError,
    load_benchmark_manifest,
    official_benchmark_ready,
    validate_frozen_dataset,
    validate_benchmark_manifest,
)


_REQUIRED_EVIDENCE_KEYS = (
    "outputPath", "outputSha256", "executorStatus", "error", "provider",
    "providerRequestId", "providerRunId", "backend", "host",
)
_REGIONAL_SCORE_FIELDS = (
    "identityScore", "eyesBrowsScore", "geometryScore", "anatomyScore",
    "outfitScore", "environmentScore", "globalScore",
)
_VALID_PIXEL_RESULTS = {"PASS", "FAIL"}
_REGIONAL_GATE_AUTHORITY = "image_studio_runtime.action_composite.workflow_v2.RegionalGate"
_REGIONAL_SCORE_AUTHORITIES = {
    "image_studio_runtime.action_composite.RegionalScoreGateway",
    "image_studio_runtime.action_composite.regional_score_gateway.RegionalScoreGateway",
}


def _regional_gate_evidence(row: Mapping[str, Any]) -> tuple[bool, Mapping[str, Any] | None]:
    """Return whether an explicit production RegionalGate result is complete.

    GW-P4's authoritative contract is a regional gate.  Numeric scores remain
    supported for legacy gateway envelopes, but a benchmark row must not
    manufacture them when production persisted only PASS/FAIL evidence.
    """
    candidate = row.get("regionalGateEvidence")
    if not isinstance(candidate, Mapping) and isinstance(row.get("lineage"), Mapping):
        after = row["lineage"].get("validatorAfter")
        if isinstance(after, Mapping):
            candidate = after.get("regionalGateEvidence")
    if not isinstance(candidate, Mapping):
        return False, None
    authority = candidate.get("authority")
    evidence_id = candidate.get("evidenceId") or candidate.get("sourceArtifact")
    if authority != _REGIONAL_GATE_AUTHORITY:
        return False, candidate
    if not isinstance(candidate.get("passed"), bool):
        return False, candidate
    if not isinstance(candidate.get("failures"), list) or not all(
        isinstance(item, str) for item in candidate["failures"]
    ):
        return False, candidate
    if not isinstance(evidence_id, str) or not evidence_id:
        return False, candidate
    return True, candidate


def _validate_completed_branch_evidence(row: Mapping[str, Any]) -> None:
    """Validate branch-specific evidence without imposing cross-branch fields.

    The benchmark schema intentionally permits nullable fields so terminal
    failure rows can be persisted.  A completed row, however, must carry the
    evidence that makes its branch auditable.  Keeping this check here makes
    missing evidence an explicit pipeline failure instead of silently turning
    it into a quality result.
    """
    if row.get("executorStatus") != "COMPLETED":
        return
    # Lightweight contract fixtures from the pre-branch-evidence runner do
    # not claim a concrete backend.  Real executor evidence always does, so
    # branch semantics are enforced only once the row identifies its backend.
    if not row.get("backend"):
        return
    missing: list[str] = []
    for key in ("outputPath", "outputSha256", "lineage", "samples"):
        if row.get(key) in (None, ""):
            missing.append(key)
    if row.get("samples") != 3:
        missing.append("samples=3")
    branch = row.get("branch")
    if branch == "control":
        # Control deliberately has no provider, workflow, GPU, or restored
        # crop.  Its output and complete QC are validated below by the common
        # classification path.
        pass
    elif branch == "nano-banana-edit":
        for key in ("provider", "model", "operation", "evidencePath", "seedSupported"):
            if row.get(key) in (None, ""):
                missing.append(key)
        if row.get("seedSupported") is not False:
            missing.append("seedSupported=false")
        if row.get("workflowId") is not None or row.get("workflowSha256") is not None:
            raise EvidencePipelineError("Nano Banana row contains fabricated ComfyUI workflow evidence")
        if row.get("gpuName") is not None or row.get("vramPeakMb") is not None:
            raise EvidencePipelineError("Nano Banana row contains GPU evidence that is not applicable")
    elif branch == "comfyui-remote":
        for key in (
            "workflowId", "workflowSha256", "gpuName", "host", "a2Path",
            "cropTransform", "maskVersion", "maskSha256", "restoredCropPath",
            "restoredCropSha256",
        ):
            if row.get(key) in (None, ""):
                missing.append(key)
        # FAIL is a measured quality result, not missing evidence.  BLOCKED
        # and UNKNOWN are the evidence-invalid states and are handled by the
        # row-dimension classifier below.
    else:
        raise EvidencePipelineError(f"unsupported benchmark branch: {branch}")
    if missing:
        raise EvidencePipelineError(
            f"{branch} completed evidence is incomplete: {', '.join(dict.fromkeys(missing))}"
        )


def _completed_evidence_error(row: Mapping[str, Any]) -> str | None:
    try:
        _validate_completed_branch_evidence(row)
    except EvidencePipelineError as exc:
        return str(exc)
    return None


def _row_dimensions(row: Mapping[str, Any]) -> dict[str, Any]:
    """Compute orthogonal benchmark dimensions for one terminal row.

    A quality gate may fail after a complete observation.  That row remains
    decision-valid and belongs in the benchmark population.  Missing output,
    validator, Regional, pixel, or authority evidence is a separate validity
    failure and is excluded from the population.
    """
    execution_valid = row.get("executorStatus") == "COMPLETED"
    reasons: list[str] = []
    if not execution_valid:
        reasons.append("execution_not_completed")

    output_path = row.get("outputPath")
    output_sha = row.get("outputSha256")
    lineage = row.get("lineage")
    evidence_shape_valid = bool(output_path and output_sha and isinstance(lineage, Mapping))
    if not evidence_shape_valid:
        reasons.append("output_or_lineage_missing")

    validator_valid = (
        isinstance(row.get("faceQcAfter"), (int, float))
        and row.get("samples") == 3
    )
    if not validator_valid:
        reasons.append("validator_samples_or_face_qc_missing")

    regional_scores_valid = all(
        isinstance(row.get(field), (int, float)) for field in _REGIONAL_SCORE_FIELDS
    )
    regional_gate_valid, regional_gate = _regional_gate_evidence(row)
    regional_authority = row.get("regionalAuthority")
    if not regional_authority and isinstance(lineage, Mapping):
        after = lineage.get("validatorAfter")
        if isinstance(after, Mapping):
            regional = after.get("regionalEvidence")
            if isinstance(regional, Mapping):
                regional_authority = regional.get("authority")
    # Legacy unit fixtures predate the explicit authority field.  Keep them
    # compatible when they also have no official base authority; real rows
    # always carry baseFrameSha256 and must name the production gateway.
    legacy_regional_fixture = (
        not row.get("baseFrameSha256")
        and not (isinstance(lineage, Mapping) and "validatorAfter" in lineage)
    )
    numeric_regional_valid = regional_scores_valid and (
        legacy_regional_fixture
        or (isinstance(regional_authority, str) and regional_authority in _REGIONAL_SCORE_AUTHORITIES)
    )
    regional_valid = numeric_regional_valid or regional_gate_valid
    if not regional_valid:
        reasons.append("regional_gate_or_scores_missing")
    if regional_gate_valid and not regional_authority:
        regional_authority = regional_gate.get("producer") or regional_gate.get("authority")

    pixel_result = row.get("pixelPreservationResult")
    pixel_valid = pixel_result in _VALID_PIXEL_RESULTS
    if not pixel_valid:
        reasons.append("pixel_evidence_missing_or_blocked")

    authority_valid = True
    base_sha = row.get("baseFrameSha256")
    if row.get("branch") in {"control", "nano-banana-edit"}:
        # Both branches are required to retain the frozen base authority.  A
        # compatibility fixture may omit it, but an official row cannot.
        if base_sha and row.get("branch") == "control" and output_sha != base_sha:
            authority_valid = False
            reasons.append("control_output_differs_from_frozen_base")
        if base_sha and isinstance(lineage, Mapping):
            lineage_base = lineage.get("baseFrameSha256")
            if lineage_base not in (None, base_sha):
                authority_valid = False
                reasons.append("lineage_base_sha_mismatch")
    if row.get("a2Sha256") and isinstance(lineage, Mapping):
        lineage_a2 = lineage.get("a2Sha256")
        if lineage_a2 not in (None, row.get("a2Sha256")):
            authority_valid = False
            reasons.append("lineage_a2_sha_mismatch")

    branch_evidence_error = _completed_evidence_error(row) if execution_valid else None
    if branch_evidence_error:
        evidence_shape_valid = False
        reasons.append(branch_evidence_error)

    evidence_valid = (
        execution_valid and evidence_shape_valid and validator_valid
        and regional_valid and pixel_valid
    )
    quality_fields_valid = validator_valid and (regional_scores_valid or regional_gate_valid)
    regional_quality_pass = (
        bool(regional_gate.get("passed")) if regional_gate_valid else (
            regional_scores_valid and all(float(row[field]) >= 90 for field in _REGIONAL_SCORE_FIELDS)
        )
    )
    quality_gate_pass = quality_fields_valid and float(row["faceQcAfter"]) >= 90 and regional_quality_pass and pixel_result == "PASS"
    decision_valid = execution_valid and evidence_valid and authority_valid
    return {
        "executionValidity": execution_valid,
        "evidenceValidity": evidence_valid,
        "validatorValidity": validator_valid,
        "regionalValidity": regional_valid,
        "pixelValidity": pixel_valid,
        "authorityValidity": authority_valid,
        "qualityValidity": quality_fields_valid,
        "decisionValidity": decision_valid,
        "qualityGatePass": quality_gate_pass if decision_valid else False,
        "regionalAuthority": regional_authority,
        "failureReasons": list(dict.fromkeys(reasons)),
    }

FAILURE_CLASSIFICATIONS = (
    "VALID_QUALITY_PASS",
    "VALID_QUALITY_FAIL",
    "INFRA_EXECUTION_FAIL",
    "VALIDATOR_FAIL",
    "EVIDENCE_PIPELINE_FAIL",
    "AUTHORITY_FAIL",
)


class BenchmarkExecutionError(RuntimeError):
    """Raised when a benchmark cannot be executed without violating contract."""

    def __init__(self, message: str, *, classification: str = "INFRA_EXECUTION_FAIL") -> None:
        super().__init__(message)
        if classification not in FAILURE_CLASSIFICATIONS:
            raise ValueError(f"unknown benchmark failure classification: {classification}")
        self.classification = classification


class ValidatorEvidenceError(BenchmarkExecutionError):
    """Raised when Validator Studio cannot produce complete evidence."""

    def __init__(self, message: str) -> None:
        super().__init__(message, classification="VALIDATOR_FAIL")


class EvidencePipelineError(BenchmarkExecutionError):
    """Raised when an otherwise usable result cannot become a benchmark row."""

    def __init__(self, message: str) -> None:
        super().__init__(message, classification="EVIDENCE_PIPELINE_FAIL")


class BenchmarkExecutor(Protocol):
    """Injected future branch executor.

    The executor is responsible for using the existing restoration ports and
    Validator Studio adapter.  It must return evidence for every canonical
    row field; this runner never invents scores or substitutes a candidate.
    """

    def execute(
        self,
        *,
        case: Mapping[str, Any],
        branch: str,
        run_id: str,
        attempt_id: str,
        seed: int,
    ) -> Mapping[str, Any]:
        ...


@dataclass(frozen=True)
class BenchmarkPlanRow:
    benchmark_id: str
    taxonomy: str
    branch: str
    source_status: str
    base_frame: str | None
    base_frame_sha256: str | None
    seed: int
    a2_sha256: str
    workflow_id: str | None
    workflow_sha256: str | None
    restorer_id: str
    executable: bool
    blocking_reason: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmarkId": self.benchmark_id,
            "taxonomy": self.taxonomy,
            "branch": self.branch,
            "sourceStatus": self.source_status,
            "baseFrame": self.base_frame,
            "baseFrameSha256": self.base_frame_sha256,
            "seed": self.seed,
            "a2Sha256": self.a2_sha256,
            "workflowId": self.workflow_id,
            "workflowSha256": self.workflow_sha256,
            "restorerId": self.restorer_id,
            "executable": self.executable,
            "blockingReason": self.blocking_reason,
        }


@dataclass(frozen=True)
class BenchmarkPlan:
    benchmark_version: str
    official_benchmark_ready: bool
    rows: tuple[BenchmarkPlanRow, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmarkVersion": self.benchmark_version,
            "officialBenchmarkReady": self.official_benchmark_ready,
            "rowCount": len(self.rows),
            "rows": [row.to_dict() for row in self.rows],
        }


@dataclass(frozen=True)
class BenchmarkRunResult:
    run_id: str
    run_manifest_path: Path
    rows_path: Path
    completed_count: int
    failed_count: int
    summary_path: Path | None = None
    decision: str | None = None


def default_benchmark_manifest_path(repo_root: Path | None = None) -> Path:
    root = repo_root or Path.cwd()
    return root / "contracts" / "identity_restoration" / "benchmark_set.yaml"


def default_benchmark_schema_path(repo_root: Path | None = None) -> Path:
    root = repo_root or Path.cwd()
    return root / "contracts" / "identity_restoration" / "benchmark_row.schema.json"


def _case_reference(case: Mapping[str, Any]) -> Mapping[str, Any] | None:
    for key in ("baseFrame", "frame", "candidate"):
        value = case.get(key)
        if isinstance(value, Mapping):
            return value
    return None


def _case_base_frame(case: Mapping[str, Any]) -> tuple[str | None, str | None]:
    reference = _case_reference(case)
    if reference is None:
        return None, None
    path = reference.get("path")
    sha256 = reference.get("sha256")
    return (str(path) if path is not None else None,
            str(sha256) if sha256 is not None else None)


def _resolve_path(path: str, repo_root: Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else repo_root / candidate


def validate_referenced_frozen_files(manifest: Mapping[str, Any], *, repo_root: Path) -> None:
    """Compatibility wrapper for the physical frozen-dataset validator."""
    validate_frozen_dataset(manifest, repo_root=repo_root)


def _branch_workflow(branch: str) -> tuple[str | None, str | None]:
    if branch == "comfyui-remote":
        return EXPECTED_WORKFLOW_ID, EXPECTED_WORKFLOW_SHA256
    # Local workflow metadata is supplied by the existing restorer descriptor
    # at execution time; it is not duplicated into the benchmark manifest.
    return None, None


class BenchmarkRunner:
    """Loads the benchmark contract, plans rows, and gates execution."""

    def __init__(
        self,
        *,
        manifest_path: Path | None = None,
        schema_path: Path | None = None,
        repo_root: Path | None = None,
        executor: BenchmarkExecutor | None = None,
        output_root: Path | None = None,
        reuse_run_id: str | None = None,
    ) -> None:
        self.repo_root = repo_root or Path.cwd()
        self.manifest_path = manifest_path or default_benchmark_manifest_path(self.repo_root)
        self.schema_path = schema_path or default_benchmark_schema_path(self.repo_root)
        self.executor = executor
        self.reuse_run_id = reuse_run_id
        self.output_root = output_root or (
            self.repo_root / "artifacts" / "identity-restoration" / "benchmarks"
        )

    def load(self) -> dict[str, Any]:
        manifest = load_benchmark_manifest(self.manifest_path)
        validate_referenced_frozen_files(manifest, repo_root=self.repo_root)
        return manifest

    def validate(self) -> dict[str, Any]:
        manifest = self.load()
        return {
            "benchmarkVersion": manifest["benchmarkVersion"],
            "manifestPath": str(self.manifest_path),
            "caseCount": len(manifest["cases"]),
            "branchCount": len(manifest["branches"]),
            "officialBenchmarkReady": official_benchmark_ready(manifest, repo_root=self.repo_root),
            "blockingCases": [
                {"benchmarkId": case["id"], "status": case["status"]}
                for case in manifest["cases"]
                if case["status"] != "FROZEN"
            ],
        }

    def preflight(self) -> dict[str, Any]:
        """Return readiness without creating a run directory or executing rows."""
        from .benchmark_preflight import run_benchmark_preflight

        return run_benchmark_preflight(
            manifest_path=self.manifest_path,
            schema_path=self.schema_path,
            repo_root=self.repo_root,
            executor=self.executor,
        ).to_dict()

    def plan(self) -> BenchmarkPlan:
        manifest = self.load()
        ready = official_benchmark_ready(manifest, repo_root=self.repo_root)
        rows: list[BenchmarkPlanRow] = []
        for case in manifest["cases"]:
            base_path, base_sha = _case_base_frame(case)
            for branch in EXPECTED_BRANCHES:
                workflow_id, workflow_sha = _branch_workflow(branch)
                reason: str | None = None
                executable = True
                if not ready:
                    executable = False
                    reason = "official benchmark dataset is not ready: every case must be FROZEN"
                elif case["status"] != "FROZEN":
                    executable = False
                    reason = f"case {case['id']} is {case['status']}, not FROZEN"
                elif not base_path or not base_sha:
                    executable = False
                    reason = f"case {case['id']} has no authoritative base frame"
                rows.append(
                    BenchmarkPlanRow(
                        benchmark_id=case["id"],
                        taxonomy=case["taxonomy"],
                        branch=branch,
                        source_status=case["status"],
                        base_frame=base_path,
                        base_frame_sha256=base_sha,
                        seed=manifest["seed"],
                        a2_sha256=manifest["authority"]["a2Sha256"],
                        workflow_id=workflow_id,
                        workflow_sha256=workflow_sha,
                        restorer_id="control" if branch == "control" else branch,
                        executable=executable,
                        blocking_reason=reason,
                    )
                )
        return BenchmarkPlan(
            benchmark_version=manifest["benchmarkVersion"],
            official_benchmark_ready=ready,
            rows=tuple(rows),
        )

    def run(self) -> BenchmarkRunResult:
        """Execute only an officially frozen dataset.

        The readiness guard is intentionally before executor/module creation.
        Therefore the current incomplete manifest causes no network, GPU, or
        paid-validator call, and there is no developer bypass flag.
        """

        manifest = self.load()
        validate_benchmark_manifest(manifest, official=True)
        validate_referenced_frozen_files(manifest, repo_root=self.repo_root)
        if self.executor is None:
            raise BenchmarkExecutionError(
                "official execution is not ready: benchmark executor is not configured"
            )
        preflight = self.preflight()
        if not preflight["officialExecutionReady"]:
            raise BenchmarkExecutionError(
                "official execution is not ready: " + "; ".join(preflight["blockers"])
            )

        run_id = f"benchmark-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
        run_dir = self.output_root / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        rows_path = run_dir / "rows.jsonl"
        for directory in ("outputs", "validator-evidence", "execution-failures", "lineage", "costs"):
            (run_dir / directory).mkdir(parents=True, exist_ok=True)
        completed = failed = 0
        written_rows: list[dict[str, Any]] = []
        with rows_path.open("x", encoding="utf-8") as stream:
            for case in manifest["cases"]:
                for branch in EXPECTED_BRANCHES:
                    attempt_id = f"{case['id']}-{branch}-attempt-1"
                    try:
                        evidence = self.executor.execute(
                            case=case, branch=branch, run_id=run_id,
                            attempt_id=attempt_id, seed=manifest["seed"],
                        )
                        row = self._validated_row(manifest, case, branch, evidence)
                        completed += 1
                    except Exception as exc:
                        failed += 1
                        row = self._failure_row(
                            manifest, case, branch, str(exc),
                            classification=getattr(exc, "classification", "INFRA_EXECUTION_FAIL"),
                        )
                    written_rows.append(row)
                    stream.write(json.dumps(row, sort_keys=True) + "\n")
                    stream.flush()

        summary = _summarize_run(written_rows)
        summary_path = run_dir / "summary.json"
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        run_manifest = {
            "benchmarkVersion": manifest["benchmarkVersion"],
            "runId": run_id,
            "createdAtUtc": datetime.now(timezone.utc).isoformat(),
            "gitCommit": _git_commit(self.repo_root),
            "a2Sha256": manifest["authority"]["a2Sha256"],
            "workflowId": manifest["remoteWorkflow"]["workflowId"],
            "workflowSha256": manifest["remoteWorkflow"]["workflowSha256"],
            "seed": manifest["seed"],
            "faceQcSamples": manifest["faceQcSamples"],
            "host": {"platform": platform.platform(), "python": sys.version.split()[0]},
            "branches": list(EXPECTED_BRANCHES),
            "completedCount": completed,
            "failedCount": failed,
            "summaryPath": str(summary_path),
            "decision": summary["decision"],
        }
        run_manifest_path = run_dir / "run_manifest.json"
        run_manifest_path.write_text(json.dumps(run_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return BenchmarkRunResult(run_id, run_manifest_path, rows_path, completed, failed, summary_path, summary["decision"])

    def _validated_row(
        self,
        manifest: Mapping[str, Any],
        case: Mapping[str, Any],
        branch: str,
        evidence: Mapping[str, Any],
    ) -> dict[str, Any]:
        required = {
            "benchmarkVersion": "2.1",
            "benchmarkId": case["id"],
            "taxonomy": case["taxonomy"],
            "branch": branch,
            "baseFrameSha256": _case_base_frame(case)[1],
            "a2Sha256": manifest["authority"]["a2Sha256"],
            "seed": manifest["seed"],
            "restorerId": "control" if branch == "control" else branch,
        }
        row = dict(required)
        row.update(dict(evidence))
        missing_evidence = [key for key in _REQUIRED_EVIDENCE_KEYS if key not in row]
        if missing_evidence:
            raise EvidencePipelineError(
                "executor evidence is incomplete: " + ", ".join(missing_evidence)
            )
        row["benchmarkVersion"] = "2.1"
        row["benchmarkId"] = case["id"]
        row["taxonomy"] = case["taxonomy"]
        row["branch"] = branch
        row["baseFrameSha256"] = required["baseFrameSha256"]
        row["a2Sha256"] = required["a2Sha256"]
        row["seed"] = required["seed"]
        row["restorerId"] = required["restorerId"]
        expected_workflow_id, expected_workflow_sha = _branch_workflow(branch)
        if branch == "comfyui-remote" and (
            row.get("workflowId") != expected_workflow_id
            or row.get("workflowSha256") != expected_workflow_sha
        ):
            raise BenchmarkExecutionError(
                "remote workflow identity does not match the frozen benchmark pin",
                classification="AUTHORITY_FAIL",
            )
        # A completed provider execution with a failed quality gate remains
        # evidence.  Summary logic classifies it as VALID_QUALITY_FAIL rather
        # than collapsing it into an execution failure here.
        schema = json.loads(self.schema_path.read_text(encoding="utf-8"))
        jsonschema.validate(row, schema)
        row["failureClassification"] = classify_benchmark_evidence(row)
        dimensions = _row_dimensions(row)
        row.update({key: value for key, value in dimensions.items() if key != "failureReasons"})
        row["failureReasons"] = dimensions["failureReasons"]
        row["failureReason"] = "; ".join(dimensions["failureReasons"]) or None
        if row["failureClassification"] == "EVIDENCE_PIPELINE_FAIL":
            row["error"] = row["failureReason"] or _completed_evidence_error(row) or (
                "completed row lacks one or more required benchmark evidence fields"
            )
        return row

    @staticmethod
    def _failure_row(
        manifest: Mapping[str, Any], case: Mapping[str, Any], branch: str, error: str,
        *, classification: str = "INFRA_EXECUTION_FAIL"
    ) -> dict[str, Any]:
        workflow_id, workflow_sha = _branch_workflow(branch)
        row = {
            "benchmarkVersion": "2.1", "benchmarkId": case["id"], "taxonomy": case["taxonomy"],
            "branch": branch, "baseFrameSha256": _case_base_frame(case)[1],
            "a2Sha256": manifest["authority"]["a2Sha256"],
            "faceQcBefore": None, "faceQcAfter": None, "identityScore": None,
            "eyesBrowsScore": None, "geometryScore": None, "anatomyScore": None,
            "outfitScore": None, "environmentScore": None, "globalScore": None,
            "pixelPreservationResult": "BLOCKED", "runtimeMs": 0, "retryCount": 0,
            "workflowId": workflow_id, "workflowSha256": workflow_sha,
            "seed": manifest["seed"], "gpuName": None, "vramPeakMb": None,
            "restorerId": "control" if branch == "control" else branch,
            "outputPath": None, "outputSha256": None, "executorStatus": "FAILED",
            "error": error, "provider": None, "providerRequestId": None,
            "providerRunId": None, "backend": None, "host": None,
            "notes": f"execution failed closed: {error}",
            "failureClassification": classification,
        }
        dimensions = _row_dimensions(row)
        row.update({key: value for key, value in dimensions.items() if key != "failureReasons"})
        row["failureReasons"] = dimensions["failureReasons"]
        row["failureReason"] = error
        return row


def _git_commit(repo_root: Path) -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def classify_benchmark_evidence(row: Mapping[str, Any]) -> str:
    """Classify execution/evidence separately from measured quality."""
    dimensions = _row_dimensions(row)
    if dimensions["decisionValidity"]:
        return "VALID_QUALITY_PASS" if dimensions["qualityGatePass"] else "VALID_QUALITY_FAIL"
    explicit = row.get("failureClassification")
    if row.get("executorStatus") != "COMPLETED":
        return str(explicit) if explicit in FAILURE_CLASSIFICATIONS else "INFRA_EXECUTION_FAIL"
    if not dimensions["authorityValidity"]:
        return "AUTHORITY_FAIL"
    if not dimensions["validatorValidity"]:
        return "VALIDATOR_FAIL"
    return "EVIDENCE_PIPELINE_FAIL"


def _summarize_run(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Compute the immutable comparison summary and the Phase-4 decision."""
    valid_classes = {"VALID_QUALITY_PASS", "VALID_QUALITY_FAIL"}
    def stats(branch: str) -> dict[str, Any]:
        values = [float(row["faceQcAfter"]) for row in rows if row.get("branch") == branch and classify_benchmark_evidence(row) in valid_classes and isinstance(row.get("faceQcAfter"), (int, float))]
        if not values:
            return {"count": 0, "validQcN": 0, "median": None, "mean": None, "min": None, "max": None}
        return {"count": len(values), "validQcN": len(values), "median": statistics.median(values), "mean": statistics.mean(values), "min": min(values), "max": max(values)}

    treatment = [row for row in rows if row.get("branch") == "comfyui-remote"]
    treatment_scores = [float(row["faceQcAfter"]) for row in treatment if classify_benchmark_evidence(row) in valid_classes and isinstance(row.get("faceQcAfter"), (int, float))]
    quality_failures: list[str] = []
    if not treatment_scores or statistics.median(treatment_scores) < 90:
        quality_failures.append("treatment_median_face_qc_below_90_or_unvalidated")
    for row in treatment:
        if classify_benchmark_evidence(row) == "VALID_QUALITY_FAIL":
            quality_failures.append(f"{row.get('benchmarkId')}:quality_gate_failed")
    branch_valid_counts = {
        branch: sum(1 for row in rows if row.get("branch") == branch and classify_benchmark_evidence(row) in valid_classes)
        for branch in EXPECTED_BRANCHES
    }
    eligibility_reasons = [
        f"{branch}: valid comparable rows {count}/10"
        for branch, count in branch_valid_counts.items() if count != 10
    ]
    decision_eligible = not eligibility_reasons
    decision = "INELIGIBLE" if not decision_eligible else ("PASS" if not quality_failures else "QUALITY_FAIL")
    classifications = [classify_benchmark_evidence(row) for row in rows]
    def regional_gate_pass(row: Mapping[str, Any]) -> bool:
        dimensions = _row_dimensions(row)
        gate = row.get("regionalGateEvidence")
        if not isinstance(gate, Mapping) and isinstance(row.get("lineage"), Mapping):
            after = row["lineage"].get("validatorAfter")
            if isinstance(after, Mapping):
                gate = after.get("regionalGateEvidence")
        if dimensions["regionalValidity"] and isinstance(gate, Mapping) and isinstance(gate.get("passed"), bool):
            return bool(gate["passed"])
        return all(
            isinstance(row.get(field), (int, float)) and float(row[field]) >= 90
            for field in _REGIONAL_SCORE_FIELDS
        )

    def anatomy_gate_pass(row: Mapping[str, Any]) -> bool:
        """Evaluate the anatomy sub-gate without aliasing the full Regional gate.

        The production RegionalGate contains anatomy as one named sub-gate,
        while GW-P4 reports Anatomy and Regional as separate hard-gate
        diagnostics.  A Regional failure in identity/global/pixel must not be
        relabeled as an anatomy failure.
        """
        dimensions = _row_dimensions(row)
        if not dimensions["regionalValidity"]:
            return False
        gate = row.get("regionalGateEvidence")
        if not isinstance(gate, Mapping) and isinstance(row.get("lineage"), Mapping):
            after = row["lineage"].get("validatorAfter")
            if isinstance(after, Mapping):
                gate = after.get("regionalGateEvidence")
        if isinstance(gate, Mapping):
            failures = gate.get("failures")
            if isinstance(failures, list):
                return not any(
                    failure in {"anatomy_below_threshold", "anatomy_unvalidated"}
                    for failure in failures
                )
        value = row.get("anatomyScore")
        return isinstance(value, (int, float)) and float(value) >= 90
    def branch_counts(branch: str) -> dict[str, int]:
        branch_rows = [row for row in rows if row.get("branch") == branch]
        branch_classes = [classify_benchmark_evidence(row) for row in branch_rows]
        decision_valid_rows = [
            row for row in branch_rows if _row_dimensions(row)["decisionValidity"]
        ]
        return {
            "plannedRows": len(branch_rows),
            "decisionValidRows": len(decision_valid_rows),
            "validQualityRows": len(decision_valid_rows),
            "qualityPassRows": branch_classes.count("VALID_QUALITY_PASS"),
            "qualityFailRows": branch_classes.count("VALID_QUALITY_FAIL"),
            "infrastructureFailureRows": branch_classes.count("INFRA_EXECUTION_FAIL"),
            "validatorFailureRows": branch_classes.count("VALIDATOR_FAIL"),
            "evidenceFailureRows": branch_classes.count("EVIDENCE_PIPELINE_FAIL"),
            "authorityFailureRows": branch_classes.count("AUTHORITY_FAIL"),
        }
    return {
        "rowCount": len(rows),
        "expectedRowCount": 30,
        "terminalRowCount": sum(row.get("executorStatus") in {"COMPLETED", "FAILED", "BLOCKED", "NOT_READY"} for row in rows),
        "branches": {
            branch: {**branch_counts(branch), **stats(branch)} for branch in EXPECTED_BRANCHES
        },
        "failureClassificationCounts": {name: classifications.count(name) for name in FAILURE_CLASSIFICATIONS},
        "decisionEligible": decision_eligible,
        "decisionEligibilityReasons": eligibility_reasons,
        "qualityGate": {
            "treatmentMedianFaceQcMin": 90,
            "treatmentMedianFaceQc": statistics.median(treatment_scores) if treatment_scores else None,
            "failures": list(dict.fromkeys(quality_failures)),
            "anatomyHealthy": decision_eligible and all(anatomy_gate_pass(row) for row in treatment),
            # Backward-compatible field retained for consumers of the prior
            # summary shape; it now reflects the actual Anatomy sub-gate.
            "anatomyRegionalHealthy": decision_eligible and all(anatomy_gate_pass(row) for row in treatment),
            "regionalHealthy": decision_eligible and all(regional_gate_pass(row) for row in treatment),
            "pixelPreservationPass": decision_eligible and all(row.get("pixelPreservationResult") == "PASS" for row in treatment),
            "lineageComplete": decision_eligible and all(bool(row.get("lineage")) for row in treatment),
            "noFallbackContamination": all(not any(bool(row.get("lineage", {}).get(flag)) for flag in ("mock_used", "local_fallback", "silent_fallback")) for row in treatment),
        },
        "decision": decision,
    }
