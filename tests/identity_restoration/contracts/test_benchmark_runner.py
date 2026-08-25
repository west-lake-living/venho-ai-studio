from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest
import yaml
from PIL import Image

from identity_restoration.application.benchmark_runner import (
    BenchmarkExecutionError, BenchmarkRunner, _summarize_run, classify_benchmark_evidence,
)
from identity_restoration.application.benchmark_contract import (
    EXPECTED_A2_SHA256,
    EXPECTED_WORKFLOW_ID,
    EXPECTED_WORKFLOW_SHA256,
)
from identity_restoration.interface.cli import main


REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST = REPO_ROOT / "contracts" / "identity_restoration" / "benchmark_set.yaml"


def test_cli_benchmark_validate_is_structurally_valid_and_ready(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["benchmark", "validate", "--manifest", str(MANIFEST)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["officialBenchmarkReady"] is True
    assert output["blockingCases"] == []


def test_cli_benchmark_plan_is_exactly_30_rows_and_all_dataset_rows_executable(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["benchmark", "plan", "--manifest", str(MANIFEST)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["rowCount"] == 30
    assert len(output["rows"]) == 30
    assert all(row["executable"] is True for row in output["rows"])
    assert all(row["blockingReason"] is None for row in output["rows"])


def test_cli_benchmark_run_composes_executor_and_refuses_only_at_external_readiness(capsys: pytest.CaptureFixture[str]) -> None:
    runner = BenchmarkRunner(manifest_path=MANIFEST)
    with pytest.raises(BenchmarkExecutionError, match="executor is not configured"):
        runner.run()

    assert main(["benchmark", "run", "--manifest", str(MANIFEST)]) == 1
    error = capsys.readouterr().err
    assert "executor is not configured" not in error
    assert "official execution is not ready" in error


def _frozen_manifest(tmp_path: Path) -> tuple[Path, Path]:
    base = tmp_path / "base.png"
    Image.new("RGB", (8, 8), (20, 30, 40)).save(base)
    base_sha = hashlib.sha256(base.read_bytes()).hexdigest()
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    for case in manifest["cases"]:
        case["status"] = "FROZEN"
        case["baseFrame"] = {
            "path": str(base), "sha256": base_sha, "width": 8, "height": 8,
            "provenance": "unit-test fixture",
        }
        case["intentionalDuplicateSource"] = True
        case.pop("candidate", None)
    path = tmp_path / "benchmark_set.yaml"
    path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    return path, base


class CompleteFixtureExecutor:
    def capabilities(self):
        fields = [
            "outputPath", "outputSha256", "executorStatus", "error", "provider",
            "providerRequestId", "providerRunId", "backend", "host",
        ]
        capabilities = {
            branch: {
                "executorPath": f"tests.CompleteFixtureExecutor.{branch}",
                "physicalCallable": True,
                "evidenceWriter": True,
                "evidenceFields": fields,
                "ready": True,
                "blockers": [],
            }
            for branch in ("control", "nano-banana-edit", "comfyui-remote")
        }
        capabilities["nano-banana-edit"].update({
            "providerConfigured": True,
            "fallbackEnabled": False,
            "evidenceFields": fields + [
                "operation", "model", "seedSupported", "lineage", "evidencePath",
            ],
        })
        return capabilities

    def execute(self, *, case, branch, run_id, attempt_id, seed):
        remote = branch == "comfyui-remote"
        return {
            "faceQcBefore": 90.0, "faceQcAfter": 91.0,
            "identityScore": 90.0, "eyesBrowsScore": 90.0,
            "geometryScore": 90.0, "anatomyScore": 90.0,
            "outfitScore": 90.0, "environmentScore": 90.0,
            "globalScore": 90.0, "pixelPreservationResult": "PASS",
            "runtimeMs": 1, "retryCount": 0,
            "workflowId": EXPECTED_WORKFLOW_ID if remote else None,
            "workflowSha256": EXPECTED_WORKFLOW_SHA256 if remote else None,
            "gpuName": "fixture", "vramPeakMb": None,
            "outputPath": "fixture.png", "outputSha256": "0" * 64,
            "executorStatus": "COMPLETED", "error": None,
            "provider": "fixture", "providerRequestId": None,
            "providerRunId": run_id, "backend": branch, "host": {},
        }


def test_future_execution_uses_injected_executor_and_writes_append_only_results(tmp_path: Path) -> None:
    manifest_path, _ = _frozen_manifest(tmp_path)
    (tmp_path / "config/projects/venho_hotel/identity_restoration").mkdir(parents=True)
    shutil.copy(
        REPO_ROOT / "config/projects/venho_hotel/identity_restoration/workflow_pins.yaml",
        tmp_path / "config/projects/venho_hotel/identity_restoration/workflow_pins.yaml",
    )
    (tmp_path / "identity_restoration/workflows").mkdir(parents=True)
    shutil.copy(
        REPO_ROOT / "identity_restoration/workflows/face_restore_win_sd15_ipadapter_v2.api.json",
        tmp_path / "identity_restoration/workflows/face_restore_win_sd15_ipadapter_v2.api.json",
    )
    output_root = tmp_path / "runs"
    result = BenchmarkRunner(
        manifest_path=manifest_path,
        repo_root=tmp_path,
        schema_path=REPO_ROOT / "contracts" / "identity_restoration" / "benchmark_row.schema.json",
        executor=CompleteFixtureExecutor(),
        output_root=output_root,
    ).run()
    assert result.completed_count == 30
    assert result.failed_count == 0
    rows = result.rows_path.read_text(encoding="utf-8").splitlines()
    assert len(rows) == 30
    assert json.loads(rows[0])["a2Sha256"] == EXPECTED_A2_SHA256
    assert result.run_manifest_path.is_file()


def _evidence_row(branch: str, *, face: float = 95.0, quality: float = 95.0) -> dict:
    return {
        "benchmarkId": "B01", "branch": branch, "executorStatus": "COMPLETED",
        "outputPath": "/tmp/output.png", "outputSha256": "a" * 64,
        "lineage": {"baseFrameSha256": "b" * 64}, "faceQcAfter": face, "samples": 3,
        "pixelPreservationResult": "PASS", "identityScore": quality,
        "eyesBrowsScore": quality, "geometryScore": quality, "anatomyScore": quality,
        "outfitScore": quality, "environmentScore": quality, "globalScore": quality,
    }


def test_failure_classification_distinguishes_quality_from_infrastructure():
    assert classify_benchmark_evidence(_evidence_row("comfyui-remote")) == "VALID_QUALITY_PASS"
    failed = _evidence_row("comfyui-remote", quality=80.0)
    assert classify_benchmark_evidence(failed) == "VALID_QUALITY_FAIL"
    failed["executorStatus"] = "FAILED"
    assert classify_benchmark_evidence(failed) == "INFRA_EXECUTION_FAIL"


def test_branch_specific_evidence_does_not_fabricate_control_or_nano_runtime_fields():
    control = _evidence_row("control")
    control["backend"] = "control"
    control["provider"] = None
    assert classify_benchmark_evidence(control) == "VALID_QUALITY_PASS"

    nano = _evidence_row("nano-banana-edit")
    nano.update({
        "backend": "venho-os-gemini-interactions",
        "provider": "nano-banana-2",
        "model": "gemini-3.1-flash-image",
        "operation": "masked_edit",
        "evidencePath": "/tmp/evidence.json",
        "seedSupported": False,
        "workflowId": None,
        "workflowSha256": None,
        "gpuName": None,
        "vramPeakMb": None,
    })
    assert classify_benchmark_evidence(nano) == "VALID_QUALITY_PASS"

    remote = _evidence_row("comfyui-remote")
    remote.update({
        "backend": "comfyui-remote",
        "workflowId": EXPECTED_WORKFLOW_ID,
        "workflowSha256": EXPECTED_WORKFLOW_SHA256,
        "gpuName": "cuda:0",
        "host": {"remoteHost": "fixture"},
        "a2Path": "/tmp/A2_Front_plate.png",
        "cropTransform": {"box": [0, 0, 8, 8], "targetSize": 8},
        "maskVersion": "hierarchical_face_v1",
        "maskSha256": "c" * 64,
        "restoredCropPath": "/tmp/restored_crop.png",
        "restoredCropSha256": "d" * 64,
    })
    assert classify_benchmark_evidence(remote) == "VALID_QUALITY_PASS"


def test_control_and_nano_do_not_require_restored_crop_workflow_or_gpu():
    control = _evidence_row("control")
    control["backend"] = "control"
    control["provider"] = None
    assert "restoredCropPath" not in control
    assert classify_benchmark_evidence(control) == "VALID_QUALITY_PASS"

    nano = _evidence_row("nano-banana-edit")
    nano.update({
        "backend": "venho-os-gemini-interactions",
        "provider": "nano-banana-2", "model": "gemini-3.1-flash-image",
        "operation": "masked_edit", "evidencePath": "/tmp/evidence.json",
        "seedSupported": False, "workflowId": None, "workflowSha256": None,
        "gpuName": None, "vramPeakMb": None,
    })
    assert classify_benchmark_evidence(nano) == "VALID_QUALITY_PASS"


def test_remote_requires_frozen_workflow_evidence():
    remote = _evidence_row("comfyui-remote")
    remote.update({"backend": "comfyui-remote"})
    assert classify_benchmark_evidence(remote) == "EVIDENCE_PIPELINE_FAIL"


def test_decision_validity_is_independent_of_quality_gate_result():
    row = _evidence_row("comfyui-remote", face=86.0, quality=72.0)
    row["pixelPreservationResult"] = "FAIL"
    dimensions = __import__(
        "identity_restoration.application.benchmark_runner",
        fromlist=["_row_dimensions"],
    )._row_dimensions(row)
    assert dimensions["decisionValidity"] is True
    assert dimensions["qualityGatePass"] is False
    assert classify_benchmark_evidence(row) == "VALID_QUALITY_FAIL"


def test_valid_regional_fail_and_pixel_fail_remain_in_median_population():
    rows = []
    for case_id in range(1, 11):
        row = _evidence_row("comfyui-remote", face=88.0, quality=75.0)
        row["benchmarkId"] = f"B{case_id:02d}"
        row["pixelPreservationResult"] = "FAIL"
        rows.append(row)
    summary = _summarize_run(rows + [
        dict(_evidence_row("control"), benchmarkId=f"B{case_id:02d}")
        for case_id in range(1, 11)
    ] + [
        dict(_evidence_row("nano-banana-edit"), benchmarkId=f"B{case_id:02d}")
        for case_id in range(1, 11)
    ])
    assert summary["decisionEligible"] is True
    assert summary["branches"]["comfyui-remote"]["decisionValidRows"] == 10
    assert summary["branches"]["comfyui-remote"]["qualityFailRows"] == 10
    assert summary["branches"]["comfyui-remote"]["median"] == 88.0
    assert summary["decision"] == "QUALITY_FAIL"


def test_summary_separates_anatomy_subgate_from_full_regional_gate():
    rows = []
    for case_id in range(1, 11):
        for branch in ("control", "nano-banana-edit", "comfyui-remote"):
            row = _evidence_row(branch)
            row["benchmarkId"] = f"B{case_id:02d}"
            if branch == "comfyui-remote":
                row["regionalGateEvidence"] = {
                    "authority": "image_studio_runtime.action_composite.workflow_v2.RegionalGate",
                    "producer": "image_studio_runtime.action_composite.regional_score_gateway.RegionalScoreGateway",
                    "passed": False,
                    "failures": ["global_composite_below_threshold"],
                    "evidenceId": f"regional-{case_id}",
                }
            rows.append(row)
    summary = _summarize_run(rows)
    assert summary["qualityGate"]["anatomyHealthy"] is True
    assert summary["qualityGate"]["anatomyRegionalHealthy"] is True
    assert summary["qualityGate"]["regionalHealthy"] is False


def test_authoritative_regional_gate_can_be_decision_valid_without_fabricated_scores():
    row = _evidence_row("control")
    row.update({
        "identityScore": None, "eyesBrowsScore": None, "geometryScore": None,
        "anatomyScore": None, "outfitScore": None, "environmentScore": None,
        "globalScore": None,
        "regionalGateEvidence": {
            "authority": "image_studio_runtime.action_composite.workflow_v2.RegionalGate",
            "producer": "image_studio_runtime.action_composite.RegionalScoreGateway",
            "passed": False,
            "failures": ["anatomy_below_threshold"],
            "evidenceId": "regional-evidence-001",
        },
    })
    dimensions = __import__(
        "identity_restoration.application.benchmark_runner",
        fromlist=["_row_dimensions"],
    )._row_dimensions(row)
    assert dimensions["regionalValidity"] is True
    assert dimensions["decisionValidity"] is True
    assert dimensions["qualityGatePass"] is False
    assert classify_benchmark_evidence(row) == "VALID_QUALITY_FAIL"


def test_missing_or_untrusted_regional_gate_remains_decision_invalid():
    row = _evidence_row("control")
    row.update({field: None for field in (
        "identityScore", "eyesBrowsScore", "geometryScore", "anatomyScore",
        "outfitScore", "environmentScore", "globalScore",
    )})
    row["regionalGateEvidence"] = {
        "authority": "tests.fake.RegionalGate",
        "passed": False,
        "failures": ["anatomy_unvalidated"],
        "evidenceId": "fake",
    }
    assert classify_benchmark_evidence(row) == "EVIDENCE_PIPELINE_FAIL"


def test_summary_marks_partial_treatment_median_ineligible_instead_of_quality_fail():
    rows = []
    for case_id in range(1, 11):
        for branch in ("control", "nano-banana-edit", "comfyui-remote"):
            row = _evidence_row(branch)
            row["benchmarkId"] = f"B{case_id:02d}"
            if branch == "comfyui-remote" and case_id > 3:
                row["executorStatus"] = "FAILED"
                row["failureClassification"] = "INFRA_EXECUTION_FAIL"
            rows.append(row)
    summary = _summarize_run(rows)
    assert summary["decisionEligible"] is False
    assert summary["decision"] == "INELIGIBLE"
    assert summary["branches"]["comfyui-remote"]["validQcN"] == 3
    assert summary["branches"]["comfyui-remote"]["median"] == 95.0
    assert summary["branches"]["comfyui-remote"]["plannedRows"] == 10
    assert summary["branches"]["comfyui-remote"]["validQualityRows"] == 3
    assert summary["branches"]["comfyui-remote"]["infrastructureFailureRows"] == 7


def test_nano_reusable_artifact_skips_provider_call(tmp_path: Path):
    from identity_restoration.application.benchmark_executor import NanoBananaEditBenchmarkExecutor

    evidence = tmp_path / "evidence.json"
    output = tmp_path / "output.png"
    Image.new("RGB", (8, 8), (1, 2, 3)).save(output)
    output_sha = hashlib.sha256(output.read_bytes()).hexdigest()
    evidence.write_text(json.dumps({
        "executorStatus": "COMPLETED", "outputPath": str(output), "outputSha256": output_sha,
        "provider": "nano-banana-2", "model": "gemini-3.1-flash-image",
        "lineage": {},
    }), encoding="utf-8")
    executor = NanoBananaEditBenchmarkExecutor.__new__(NanoBananaEditBenchmarkExecutor)
    executor.reusable_evidence = {"B01": evidence}
    reused = executor._reuse_existing_evidence({"id": "B01"})
    assert reused["outputSha256"] == output_sha
    assert reused["lineage"]["artifactReuse"]["providerCallReused"] is True
