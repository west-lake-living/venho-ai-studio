from __future__ import annotations

import hashlib
import json
from pathlib import Path

import jsonschema
import pytest
import yaml
from PIL import Image

from identity_restoration.application.benchmark_contract import (
    BenchmarkManifestError,
    EXPECTED_BRANCHES,
    EXPECTED_CASE_IDS,
    load_benchmark_manifest,
    official_benchmark_ready,
    validate_frozen_dataset,
    validate_benchmark_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = REPO_ROOT / "contracts" / "identity_restoration"
FIXTURES = CONTRACTS / "fixtures" / "benchmark"
MANIFEST_PATH = CONTRACTS / "benchmark_set.yaml"
SCHEMA = json.loads((CONTRACTS / "benchmark_row.schema.json").read_text(encoding="utf-8"))


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_benchmark_manifest_parses_and_has_exact_cases_and_branches() -> None:
    manifest = load_benchmark_manifest(MANIFEST_PATH)
    assert manifest["benchmarkVersion"] == "2.1"
    assert manifest["seed"] == 42
    assert manifest["faceQcSamples"] == 3
    assert tuple(manifest["branches"]) == EXPECTED_BRANCHES
    assert tuple(case["id"] for case in manifest["cases"]) == EXPECTED_CASE_IDS
    assert manifest["authority"]["a2Sha256"] == "1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d"
    assert manifest["remoteWorkflow"]["workflowId"] == "face_restore_win_sd15_ipadapter_v2"
    assert manifest["remoteWorkflow"]["workflowSha256"] == "1a6421a04ce7bdedd716beea93d196551f5dbe77c3da11d1e8a6bc4f1f06ee58"
    assert manifest["remoteParams"] == {
        "denoise": 0.35,
        "steps": 20,
        "cfg": 6,
        "sampler": "euler",
        "scheduler": "normal",
    }


def test_official_benchmark_readiness_is_fail_closed_when_a_case_is_not_frozen() -> None:
    manifest = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest["cases"][4]["status"] = "MISSING"
    manifest["cases"][4].pop("baseFrame", None)
    assert official_benchmark_ready(manifest) is False
    with pytest.raises(BenchmarkManifestError, match="every case is FROZEN"):
        validate_benchmark_manifest(manifest, official=True)


def test_current_frozen_sources_validate_and_dataset_is_ready() -> None:
    manifest = load_benchmark_manifest(MANIFEST_PATH)
    validate_frozen_dataset(manifest, repo_root=REPO_ROOT, require_all=True)
    assert [case["id"] for case in manifest["cases"] if case["status"] == "FROZEN"] == list(EXPECTED_CASE_IDS)
    assert official_benchmark_ready(manifest, repo_root=REPO_ROOT) is True


def _single_frozen_manifest(tmp_path: Path) -> tuple[dict, Path]:
    image_path = tmp_path / "frame.png"
    Image.new("RGB", (8, 6), (10, 20, 30)).save(image_path)
    manifest = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    frame = {
        "path": str(image_path),
        "sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
        "width": 8,
        "height": 6,
        "provenance": "unit-test fixture",
    }
    manifest["cases"][0]["status"] = "FROZEN"
    manifest["cases"][0]["baseFrame"] = frame
    return manifest, image_path


def test_corrupt_frozen_image_fails_closed(tmp_path: Path) -> None:
    manifest, image_path = _single_frozen_manifest(tmp_path)
    image_path.write_bytes(b"not-an-image")
    manifest["cases"][0]["baseFrame"]["sha256"] = hashlib.sha256(image_path.read_bytes()).hexdigest()
    with pytest.raises(BenchmarkManifestError, match="cannot be decoded"):
        validate_frozen_dataset(manifest, repo_root=tmp_path)


def test_missing_frozen_file_fails_closed(tmp_path: Path) -> None:
    manifest, _ = _single_frozen_manifest(tmp_path)
    manifest["cases"][0]["baseFrame"]["path"] = str(tmp_path / "missing.png")
    with pytest.raises(BenchmarkManifestError, match="file is missing"):
        validate_frozen_dataset(manifest, repo_root=tmp_path)


def test_sha_mismatch_fails_closed(tmp_path: Path) -> None:
    manifest, _ = _single_frozen_manifest(tmp_path)
    manifest["cases"][0]["baseFrame"]["sha256"] = "0" * 64
    with pytest.raises(BenchmarkManifestError, match="SHA-256 mismatch"):
        validate_frozen_dataset(manifest, repo_root=tmp_path)


def test_wrong_dimensions_fail_closed(tmp_path: Path) -> None:
    manifest, _ = _single_frozen_manifest(tmp_path)
    manifest["cases"][0]["baseFrame"]["width"] = 99
    with pytest.raises(BenchmarkManifestError, match="dimensions mismatch"):
        validate_frozen_dataset(manifest, repo_root=tmp_path)


def test_duplicate_source_path_requires_explicit_documentation(tmp_path: Path) -> None:
    manifest, _ = _single_frozen_manifest(tmp_path)
    second = manifest["cases"][1]
    second["status"] = "FROZEN"
    second["baseFrame"] = dict(manifest["cases"][0]["baseFrame"])
    with pytest.raises(BenchmarkManifestError, match="duplicates source path"):
        validate_frozen_dataset(manifest, repo_root=tmp_path)


@pytest.mark.parametrize(
    "fixture_name",
    [
        "valid_control.json",
        "valid_comfyui_local.json",
        "valid_comfyui_remote.json",
        "valid_nano_banana_edit.json",
    ],
)
def test_v21_branch_fixtures_pass_schema(fixture_name: str) -> None:
    jsonschema.validate(_fixture(fixture_name), SCHEMA)


def test_missing_required_field_fails_schema() -> None:
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(_fixture("invalid_missing_required_field.json"), SCHEMA)


def test_unknown_property_fails_schema() -> None:
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(_fixture("invalid_unknown_property.json"), SCHEMA)


def test_schema_itself_is_valid_and_remains_fail_closed() -> None:
    jsonschema.Draft202012Validator.check_schema(SCHEMA)
    assert SCHEMA["additionalProperties"] is False
