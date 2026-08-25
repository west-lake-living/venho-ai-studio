from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

import yaml
from PIL import Image

BENCHMARK_VERSION = "2.1"
EXPECTED_BRANCHES = (
    "control",
    "nano-banana-edit",
    "comfyui-remote",
)
EXPECTED_CASE_IDS = tuple(f"B{i:02d}" for i in range(1, 11))
FROZEN_STATUS = "FROZEN"
EXPECTED_A2_SHA256 = "1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d"
EXPECTED_WORKFLOW_ID = "face_restore_win_sd15_ipadapter_v2"
EXPECTED_WORKFLOW_SHA256 = "1a6421a04ce7bdedd716beea93d196551f5dbe77c3da11d1e8a6bc4f1f06ee58"
EXPECTED_REMOTE_PARAMS = {
    "denoise": 0.35,
    "steps": 20,
    "cfg": 6,
    "sampler": "euler",
    "scheduler": "normal",
}


class BenchmarkManifestError(ValueError):
    """Raised when the benchmark manifest is invalid or not ready."""


def load_benchmark_manifest(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise BenchmarkManifestError("benchmark manifest must be a mapping")
    validate_benchmark_manifest(payload)
    return payload


def validate_benchmark_manifest(manifest: Mapping[str, Any], *, official: bool = False) -> None:
    """Validate the contract without running or authoring a benchmark.

    ``official=True`` is deliberately fail-closed until every case is frozen.
    This is a contract guard only; it does not implement benchmark execution.
    """
    if manifest.get("benchmarkVersion") != BENCHMARK_VERSION:
        raise BenchmarkManifestError("benchmarkVersion must be 2.1")
    if manifest.get("seed") != 42:
        raise BenchmarkManifestError("benchmark seed must be 42")
    if manifest.get("faceQcSamples") != 3:
        raise BenchmarkManifestError("faceQcSamples must be 3")

    authority = manifest.get("authority")
    if not isinstance(authority, Mapping) or authority.get("a2Sha256") != EXPECTED_A2_SHA256:
        raise BenchmarkManifestError("A2 authority hash does not match the frozen authority")

    workflow = manifest.get("remoteWorkflow")
    if (
        not isinstance(workflow, Mapping)
        or workflow.get("workflowId") != EXPECTED_WORKFLOW_ID
        or workflow.get("workflowSha256") != EXPECTED_WORKFLOW_SHA256
    ):
        raise BenchmarkManifestError("remote workflow authority does not match the frozen pin")

    if manifest.get("remoteParams") != EXPECTED_REMOTE_PARAMS:
        raise BenchmarkManifestError("remoteParams do not match the frozen contract")

    if tuple(manifest.get("branches", ())) != EXPECTED_BRANCHES:
        raise BenchmarkManifestError("benchmark branches must be exactly the three official decision branches")

    cases = manifest.get("cases")
    if not isinstance(cases, list):
        raise BenchmarkManifestError("benchmark cases must be a list")
    if len(cases) != len(EXPECTED_CASE_IDS):
        raise BenchmarkManifestError("benchmark cases must contain exactly ten entries")
    case_ids = tuple(case.get("id") for case in cases if isinstance(case, Mapping))
    if case_ids != EXPECTED_CASE_IDS:
        raise BenchmarkManifestError("benchmark cases must be exactly B01 through B10 in order")
    for case in cases:
        if not isinstance(case, Mapping) or case.get("status") not in {"MISSING", "CANDIDATE_NOT_FROZEN", FROZEN_STATUS}:
            raise BenchmarkManifestError("each benchmark case must have a recognized readiness status")

    if official and not official_benchmark_ready(manifest):
        raise BenchmarkManifestError("official benchmark is blocked until every case is FROZEN")


def validate_frozen_dataset(
    manifest: Mapping[str, Any], *, repo_root: Path | None = None, require_all: bool = False
) -> None:
    """Validate the physical source files referenced by frozen cases.

    This is deliberately local and deterministic. It does not inspect Face QC
    and never changes a case's readiness status.
    """
    root = repo_root or Path.cwd()
    cases = manifest.get("cases")
    if not isinstance(cases, list) or len(cases) != len(EXPECTED_CASE_IDS):
        raise BenchmarkManifestError("dataset must contain exactly B01-B10")

    seen_paths: dict[str, str] = {}
    for case in cases:
        if not isinstance(case, Mapping):
            raise BenchmarkManifestError("each benchmark case must be a mapping")
        case_id = case["id"]
        if case.get("status") != FROZEN_STATUS:
            if require_all:
                raise BenchmarkManifestError(f"{case_id} is {case.get('status')}, not FROZEN")
            continue

        frame = case.get("baseFrame")
        if not isinstance(frame, Mapping):
            raise BenchmarkManifestError(f"{case_id} is FROZEN but baseFrame is missing")
        path_text = frame.get("path")
        expected_sha = frame.get("sha256")
        expected_width = frame.get("width")
        expected_height = frame.get("height")
        provenance = frame.get("provenance")
        if not isinstance(path_text, str) or not path_text:
            raise BenchmarkManifestError(f"{case_id} FROZEN baseFrame.path is missing")
        if not isinstance(expected_sha, str) or len(expected_sha) != 64:
            raise BenchmarkManifestError(f"{case_id} FROZEN baseFrame.sha256 is missing or malformed")
        if not isinstance(expected_width, int) or not isinstance(expected_height, int):
            raise BenchmarkManifestError(f"{case_id} FROZEN baseFrame dimensions are missing")
        if not isinstance(provenance, str) or not provenance.strip():
            raise BenchmarkManifestError(f"{case_id} FROZEN baseFrame.provenance is missing")

        path = Path(path_text)
        if not path.is_absolute():
            path = root / path
        key = str(path.resolve())
        if key in seen_paths and not case.get("intentionalDuplicateSource"):
            raise BenchmarkManifestError(
                f"{case_id} duplicates source path used by {seen_paths[key]} without documentation"
            )
        seen_paths[key] = case_id
        if not path.is_file():
            raise BenchmarkManifestError(f"{case_id} frozen source file is missing: {path}")

        actual_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_sha != expected_sha:
            raise BenchmarkManifestError(
                f"{case_id} SHA-256 mismatch: expected {expected_sha}, got {actual_sha}"
            )
        try:
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                actual_size = image.size
        except Exception as exc:
            raise BenchmarkManifestError(f"{case_id} image cannot be decoded: {path}") from exc
        if actual_size != (expected_width, expected_height):
            raise BenchmarkManifestError(
                f"{case_id} dimensions mismatch: expected {expected_width}x{expected_height}, "
                f"got {actual_size[0]}x{actual_size[1]}"
            )


def official_benchmark_ready(manifest: Mapping[str, Any], *, repo_root: Path | None = None) -> bool:
    try:
        validate_benchmark_manifest(manifest, official=False)
    except BenchmarkManifestError:
        return False
    cases = manifest.get("cases")
    if not (
        isinstance(cases, list)
        and tuple(case.get("id") for case in cases if isinstance(case, Mapping)) == EXPECTED_CASE_IDS
        and all(case.get("status") == FROZEN_STATUS for case in cases)
    ):
        return False
    try:
        validate_frozen_dataset(manifest, repo_root=repo_root, require_all=True)
    except BenchmarkManifestError:
        return False
    return True
