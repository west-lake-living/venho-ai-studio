from __future__ import annotations

"""Fail-closed readiness inspection for the GW-P4 benchmark.

This module only inspects configuration, static adapter paths, and injected
executor capabilities. It never submits a benchmark row or calls a paid
validator/provider.
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .benchmark_contract import (
    EXPECTED_A2_SHA256,
    EXPECTED_BRANCHES,
    EXPECTED_WORKFLOW_ID,
    EXPECTED_WORKFLOW_SHA256,
    BenchmarkManifestError,
    load_benchmark_manifest,
    official_benchmark_ready,
    validate_frozen_dataset,
)
from .benchmark_executor import REQUIRED_EVIDENCE_KEYS, REMOTE_EVIDENCE_KEYS, NANO_BANANA_EVIDENCE_KEYS


@dataclass(frozen=True)
class BranchCapability:
    branch: str
    executor: str | None
    adapter: str | None
    registered: bool
    physical_callable: bool
    evidence_writer: bool
    evidence_fields: tuple[str, ...]
    ready: bool
    blockers: tuple[str, ...]
    bootstrap_smoke_allowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "branch": self.branch,
            "executor": self.executor,
            "adapter": self.adapter,
            "registered": self.registered,
            "physicalCallable": self.physical_callable,
            "evidenceWriter": self.evidence_writer,
            "evidenceFields": list(self.evidence_fields),
            "ready": self.ready,
            "blockers": list(self.blockers),
            "bootstrapSmokeAllowed": self.bootstrap_smoke_allowed,
        }


@dataclass(frozen=True)
class BenchmarkPreflight:
    official_benchmark_ready: bool
    executor_ready: bool
    official_execution_ready: bool
    schema_compatible: bool
    workflow_authority: dict[str, Any]
    environment: dict[str, Any]
    branches: tuple[BranchCapability, ...]
    blockers: tuple[str, ...]
    bootstrap_smoke_allowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "officialBenchmarkReady": self.official_benchmark_ready,
            "executorReady": self.executor_ready,
            "officialExecutionReady": self.official_execution_ready,
            "schemaCompatible": self.schema_compatible,
            "workflowAuthority": self.workflow_authority,
            "environment": self.environment,
            "branches": [branch.to_dict() for branch in self.branches],
            "blockers": list(self.blockers),
            "bootstrapSmokeAllowed": self.bootstrap_smoke_allowed,
        }


def run_benchmark_preflight(
    *,
    manifest_path: Path,
    schema_path: Path,
    repo_root: Path,
    executor: Any = None,
) -> BenchmarkPreflight:
    manifest = load_benchmark_manifest(manifest_path)
    dataset_ready = official_benchmark_ready(manifest, repo_root=repo_root)
    schema_compatible, schema_blockers = _check_schema(schema_path)
    workflow_authority = _check_workflow_authority(repo_root)
    env = _read_environment()
    supplied = _executor_capabilities(executor)

    branches = (
        _control_capability(supplied),
        _comfyui_capability("comfyui-local", supplied, env, workflow_authority, repo_root),
        _comfyui_capability("comfyui-remote", supplied, env, workflow_authority, repo_root),
        _nano_capability(supplied, env, repo_root),
    )
    blockers = list(schema_blockers)
    if not dataset_ready:
        blockers.append("authoritative benchmark dataset is not ready")
    if not workflow_authority.get("valid"):
        blockers.append(str(workflow_authority.get("error", "workflow authority is invalid")))
    blockers.extend(f"{branch.branch}: {reason}" for branch in branches for reason in branch.blockers)
    executor_ready = all(branch.ready for branch in branches) and schema_compatible
    bootstrap_allowed = any(
        branch.branch == "comfyui-remote" and branch.bootstrap_smoke_allowed
        for branch in branches
    )
    return BenchmarkPreflight(
        official_benchmark_ready=dataset_ready,
        executor_ready=executor_ready,
        official_execution_ready=dataset_ready and executor_ready,
        schema_compatible=schema_compatible,
        workflow_authority=workflow_authority,
        environment=env,
        branches=branches,
        blockers=tuple(dict.fromkeys(blockers)),
        bootstrap_smoke_allowed=bootstrap_allowed,
    )


def _executor_capabilities(executor: Any) -> Mapping[str, Mapping[str, Any]]:
    if executor is None:
        return {}
    method = getattr(executor, "capabilities", None)
    if not callable(method):
        return {}
    value = method()
    return value if isinstance(value, Mapping) else {}


def _from_supplied(branch: str, supplied: Mapping[str, Mapping[str, Any]]) -> BranchCapability | None:
    raw = supplied.get(branch)
    if not isinstance(raw, Mapping):
        return None
    fields = tuple(str(value) for value in raw.get("evidenceFields", ()))
    blockers = [str(value) for value in raw.get("blockers", ())]
    if not raw.get("physicalCallable", False):
        blockers.append("injected executor is not physically callable")
    if not raw.get("evidenceWriter", False):
        blockers.append("injected executor has no evidence writer")
    missing_fields = sorted(set(REQUIRED_EVIDENCE_KEYS) - set(fields))
    if missing_fields:
        blockers.append("injected evidence is missing: " + ", ".join(missing_fields))
    return BranchCapability(
        branch=branch,
        executor=str(raw.get("executorPath")) if raw.get("executorPath") else None,
        adapter=str(raw.get("adapterPath")) if raw.get("adapterPath") else None,
        registered=bool(raw.get("registered", True)),
        physical_callable=bool(raw.get("physicalCallable", False)),
        evidence_writer=bool(raw.get("evidenceWriter", False)),
        evidence_fields=fields,
        ready=bool(raw.get("ready", False)) and not blockers,
        blockers=tuple(blockers),
        bootstrap_smoke_allowed=bool(raw.get("bootstrapSmokeAllowed", False)) and not blockers,
    )


def _control_capability(supplied: Mapping[str, Mapping[str, Any]]) -> BranchCapability:
    return _from_supplied("control", supplied) or BranchCapability(
        branch="control",
        executor="identity_restoration.application.benchmark_executor.ControlBenchmarkExecutor",
        adapter=None,
        registered=True,
        physical_callable=True,
        evidence_writer=True,
        evidence_fields=REQUIRED_EVIDENCE_KEYS,
        ready=True,
        blockers=(),
    )


def _comfyui_capability(
    branch: str,
    supplied: Mapping[str, Mapping[str, Any]],
    env: Mapping[str, Any],
    workflow: Mapping[str, Any],
    repo_root: Path,
) -> BranchCapability:
    injected = _from_supplied(branch, supplied)
    if injected is not None:
        return injected
    if branch == "comfyui-local":
        return BranchCapability(
            branch=branch,
            executor="identity_restoration.application.benchmark_executor.ComfyUILocalBenchmarkExecutor",
            adapter="identity_restoration.infrastructure.restorers.comfyui_local_restorer.ComfyUILocalRestorer",
            registered=True,
            physical_callable=True,
            evidence_writer=True,
            evidence_fields=REQUIRED_EVIDENCE_KEYS,
            ready=True,
            blockers=(),
        )
    blockers = []
    if branch == "comfyui-remote":
        smoke_path = _find_valid_physical_smoke(repo_root, "comfyui-remote")
        if smoke_path is None:
            blockers.append("remote physical smoke evidence has not been recorded")
        if not env["comfyuiRemoteEnabled"] and smoke_path is None:
            blockers.append("IDR_COMFYUI_REMOTE_ENABLED is false in the preflight environment")
        if not workflow.get("valid"):
            blockers.append("frozen remote workflow authority cannot be verified")
        return BranchCapability(
            branch=branch,
            executor="identity_restoration.application.benchmark_executor.ComfyUIRemoteBenchmarkExecutor",
            adapter=(
                "identity_restoration.infrastructure.restorers."
                "comfyui_remote_restorer.ComfyUIRemoteRestorer"
            ),
            registered=True,
            physical_callable=True,
            evidence_writer=True,
            evidence_fields=REMOTE_EVIDENCE_KEYS,
            ready=not blockers,
            blockers=tuple(blockers),
            bootstrap_smoke_allowed=False,
        )
    return BranchCapability(
        branch=branch,
        executor=None,
        adapter=(
            "identity_restoration.infrastructure.restorers.comfyui_local_restorer.ComfyUILocalRestorer"
            if branch == "comfyui-local"
            else "identity_restoration.infrastructure.restorers.comfyui_remote_restorer.ComfyUIRemoteRestorer"
        ),
        registered=False,
        physical_callable=False,
        evidence_writer=False,
        evidence_fields=(),
        ready=False,
        blockers=tuple(blockers),
    )


def _nano_capability(
    supplied: Mapping[str, Mapping[str, Any]], env: Mapping[str, Any], repo_root: Path
) -> BranchCapability:
    injected = _from_supplied("nano-banana-edit", supplied)
    if injected is not None:
        raw = supplied["nano-banana-edit"]
        blockers = list(injected.blockers)
        reuse_only = bool(raw.get("reuseOnly", False))
        if not reuse_only and not raw.get("providerConfigured", False):
            blockers.append("Nano Banana provider configuration is unavailable")
        if raw.get("fallbackEnabled", False):
            blockers.append("Nano Banana fallback path is enabled")
        fields = tuple(str(value) for value in raw.get("evidenceFields", ()))
        missing_fields = sorted(set(NANO_BANANA_EVIDENCE_KEYS) - set(fields))
        if missing_fields:
            blockers.append("Nano Banana evidence is missing: " + ", ".join(missing_fields))
        return BranchCapability(
            branch=injected.branch,
            executor=injected.executor,
            adapter=injected.adapter,
            registered=injected.registered,
            physical_callable=injected.physical_callable,
            evidence_writer=injected.evidence_writer,
            evidence_fields=fields,
            ready=injected.ready and not blockers,
            blockers=tuple(dict.fromkeys(blockers)),
            bootstrap_smoke_allowed=False,
        )
    smoke_path = _find_valid_physical_smoke(repo_root, "nano-banana-edit")
    if smoke_path is not None:
        return BranchCapability(
            branch="nano-banana-edit",
            executor="identity_restoration.application.benchmark_executor.NanoBananaEditBenchmarkExecutor",
            adapter="identity_restoration.infrastructure.restorers.nano_banana_edit_adapter.NanoBananaEditAdapter",
            registered=True,
            physical_callable=True,
            evidence_writer=True,
            evidence_fields=NANO_BANANA_EVIDENCE_KEYS,
            ready=True,
            blockers=(),
        )
    return BranchCapability(
        branch="nano-banana-edit",
        executor="identity_restoration.application.benchmark_executor.NanoBananaEditBenchmarkExecutor",
        adapter="existing Venho OS Nano Banana masked-edit/action-composite path (injected port)",
        registered=False,
        physical_callable=False,
        evidence_writer=False,
        evidence_fields=(),
        ready=False,
        blockers=(
            "existing Nano Banana/action-composite provider path is not registered in this Python composition root",
            "smallest fix: inject NanoBananaEditPort from the existing provider path",
        ),
    )


def _find_valid_physical_smoke(repo_root: Path, branch: str) -> Path | None:
    """Accept only persisted, self-verifying NON_BENCHMARK smoke evidence."""
    evidence_root = repo_root / "evidence"
    if not evidence_root.is_dir():
        return None
    if branch == "nano-banana-edit":
        candidates = evidence_root.glob("gw-p4-t0-5-3b-*/**/smoke_manifest.json")
    elif branch == "comfyui-remote":
        candidates = evidence_root.glob("gw-p4-t0-5-2d-*/smoke_manifest.json")
    else:
        return None
    for path in sorted(candidates, reverse=True):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if _valid_physical_smoke_payload(payload, branch, repo_root):
                return path
        except (OSError, ValueError, TypeError):
            continue
    return None


def _valid_physical_smoke_payload(payload: Mapping[str, Any], branch: str, repo_root: Path) -> bool:
    if branch == "nano-banana-edit":
        if payload.get("branch") != branch or payload.get("benchmarkId") != "B01":
            return False
        if payload.get("evidenceType") != "NON_BENCHMARK" or payload.get("phase") != "PREFLIGHT":
            return False
        if payload.get("executorStatus") != "COMPLETED":
            return False
        if payload.get("provider") != "nano-banana-2" or payload.get("model") != "gemini-3.1-flash-image":
            return False
        if payload.get("baseFrameSha256") != "e7b00d4a65b2cc97e274e3c00f96e091bda0e614778df5a2d43f17cc3793faf9":
            return False
        if payload.get("a2Sha256") != EXPECTED_A2_SHA256:
            return False
        if payload.get("geometryModelSha256") != "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4":
            return False
        if payload.get("maskVersion") != "hierarchical_face_v1":
            return False
        if payload.get("paidCallCount", 0) < 1 or payload.get("seed") != 42:
            return False
        if any(payload.get(key) is True for key in ("mockUsed", "fallbackUsed", "localFallback", "silentFallback")):
            return False
        return _valid_output_artifact(payload, repo_root)

    evidence = payload.get("evidence")
    if not isinstance(evidence, Mapping):
        return False
    nested = evidence.get("lineage", {}).get("restoration", {}) if isinstance(evidence.get("lineage"), Mapping) else {}
    return (
        payload.get("branch") == branch
        and payload.get("caseId") == "B01"
        and payload.get("evidenceType") == "NON_BENCHMARK"
        and payload.get("phase") == "PREFLIGHT"
        and evidence.get("executorStatus") == "COMPLETED"
        and evidence.get("provider") == branch
        and evidence.get("workflowId") == EXPECTED_WORKFLOW_ID
        and evidence.get("workflowSha256") == EXPECTED_WORKFLOW_SHA256
        and nested.get("promptId")
        and payload.get("a2Sha256") == EXPECTED_A2_SHA256
        and _valid_output_artifact(evidence, repo_root)
    )


def _valid_output_artifact(payload: Mapping[str, Any], repo_root: Path) -> bool:
    output = payload.get("outputPath")
    expected_sha = payload.get("outputSha256")
    if not isinstance(output, str) or not isinstance(expected_sha, str):
        return False
    path = Path(output)
    if not path.is_absolute():
        path = repo_root / path
    try:
        return path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == expected_sha
    except OSError:
        return False


def _check_schema(schema_path: Path) -> tuple[bool, tuple[str, ...]]:
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return False, (f"benchmark row schema cannot be loaded: {exc}",)
    required = set(schema.get("required", ()))
    properties = set(schema.get("properties", ()))
    canonical = {
        "benchmarkId", "taxonomy", "branch", "baseFrameSha256", "a2Sha256", "restorerId",
        "workflowId", "workflowSha256", "seed", "runtimeMs", "retryCount", "gpuName", "vramPeakMb",
        *REQUIRED_EVIDENCE_KEYS,
    }
    missing = sorted(canonical - properties)
    if missing:
        return False, (f"benchmark row schema lacks evidence properties: {', '.join(missing)}",)
    if not required.intersection({"benchmarkId", "branch", "baseFrameSha256", "a2Sha256"}):
        return False, ("benchmark row schema lost canonical required identity fields",)
    return True, ()


def _check_workflow_authority(repo_root: Path) -> dict[str, Any]:
    pins_path = repo_root / "config/projects/venho_hotel/identity_restoration/workflow_pins.yaml"
    workflow_path = repo_root / "identity_restoration/workflows" / f"{EXPECTED_WORKFLOW_ID}.api.json"
    try:
        actual = hashlib.sha256(workflow_path.read_bytes()).hexdigest()
        pins_text = pins_path.read_text(encoding="utf-8")
        expected = EXPECTED_WORKFLOW_SHA256 if EXPECTED_WORKFLOW_ID in pins_text else None
        valid = actual == EXPECTED_WORKFLOW_SHA256 and expected == EXPECTED_WORKFLOW_SHA256
        return {
            "workflowId": EXPECTED_WORKFLOW_ID,
            "workflowSha256": actual,
            "expectedSha256": EXPECTED_WORKFLOW_SHA256,
            "valid": valid,
            "error": None if valid else "workflow file/pin does not match frozen authority",
        }
    except OSError as exc:
        return {"workflowId": EXPECTED_WORKFLOW_ID, "valid": False, "error": str(exc)}


def _read_environment() -> dict[str, Any]:
    import os

    return {
        "comfyuiEnabled": os.environ.get("IDR_COMFYUI_ENABLED", "false").lower() in {"1", "true", "yes", "on"},
        "comfyuiRemoteEnabled": os.environ.get("IDR_COMFYUI_REMOTE_ENABLED", "false").lower() in {"1", "true", "yes", "on"},
        "comfyuiBaseUrlConfigured": bool(os.environ.get("IDR_COMFYUI_BASE_URL", "http://127.0.0.1:8188")),
        "comfyuiRemoteBaseUrlConfigured": bool(os.environ.get("IDR_COMFYUI_REMOTE_BASE_URL", "http://127.0.0.1:8188")),
        "nanoBananaEnabled": os.environ.get("IDR_NANO_BANANA_ENABLED", "false").lower() in {"1", "true", "yes", "on"},
    }
