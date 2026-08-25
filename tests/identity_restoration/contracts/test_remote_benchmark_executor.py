from __future__ import annotations

import hashlib
import inspect
import json
from io import BytesIO
from pathlib import Path

import pytest
import jsonschema
from PIL import Image

from identity_restoration.application.benchmark_executor import (
    ComfyUIRemoteBenchmarkExecutor,
    ComfyUILocalBenchmarkExecutor,
)
from identity_restoration.application.benchmark_runner import BenchmarkExecutionError
from identity_restoration.application.dto.restore_command import RestoreCommand
from identity_restoration.application.dto.restoration_result import RestorationResult
from identity_restoration.domain.entities import CropTransform, MaskSet
from identity_restoration.domain.policies.pixel_preservation import PixelLockReport
from identity_restoration.domain.value_objects import RestorationParams
from identity_restoration.application.ports.worker_health import WorkerHealth, WorkerStatus


REPO_ROOT = Path(__file__).resolve().parents[3]
A2_SHA = "1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d"
WORKFLOW_ID = "face_restore_win_sd15_ipadapter_v2"
WORKFLOW_SHA = "1a6421a04ce7bdedd716beea93d196551f5dbe77c3da11d1e8a6bc4f1f06ee58"


def _png(size=(8, 8), color=(20, 30, 40, 255)) -> bytes:
    out = BytesIO()
    Image.new("RGBA", size, color).save(out, format="PNG")
    return out.getvalue()


def _case(tmp_path: Path) -> tuple[dict, bytes]:
    base = tmp_path / "base.png"
    base.write_bytes(_png())
    data = base.read_bytes()
    return {
        "id": "B04",
        "taxonomy": "Running Front 3/4",
        "status": "FROZEN",
        "baseFrame": {
            "path": str(base),
            "sha256": hashlib.sha256(data).hexdigest(),
            "width": 8,
            "height": 8,
            "provenance": "test fixture",
        },
    }, data


def _command_factory(base_png: bytes, branch: str):
    def factory(case, run_id, attempt_id, seed):
        mask = _png(color=(255, 255, 255, 255))
        return RestoreCommand(
            run_id=run_id,
            attempt_id=attempt_id,
            restorer_id=branch,
            crop_png=base_png,
            mask=MaskSet(editable=mask, feather=mask, version="test-mask-v1"),
            full_canvas_mask=MaskSet(editable=mask, feather=mask, version="test-full-mask-v1"),
            base_canvas_png=base_png,
            crop_transform=CropTransform.from_box(0, 0, 8, 8, 8),
            a2_path="/canonical/A2_Front_plate.png",
            a2_sha256=A2_SHA,
            workflow_id=WORKFLOW_ID if branch == "comfyui-remote" else "face_restore_v1_api",
            seed=seed,
            params=RestorationParams(denoise=0.35, steps=20, cfg=6.0, sampler="euler", scheduler="normal"),
        )

    return factory


class FakeRemoteUseCase:
    def __init__(self, root: Path, base_png: bytes):
        self.restored = root / "restored.png"
        image = Image.open(BytesIO(base_png)).convert("RGBA")
        pixel = image.getpixel((0, 0))
        image.putpixel((0, 0), (min(pixel[0] + 1, 255), pixel[1], pixel[2], pixel[3]))
        image.save(self.restored, format="PNG")
        self.composite = root / "composite.png"
        Path(self.composite).write_bytes(self.restored.read_bytes())

    def execute(self, command):
        return RestorationResult(
            run_id=command.run_id,
            attempt_id=command.attempt_id,
            status="NEEDS_REVIEW",
            restored_crop_path=str(self.restored),
            composite_path=str(self.composite),
            pixel_lock=PixelLockReport(True, 0, "0" * 64),
            lineage={
                "workflowId": WORKFLOW_ID,
                "workflowSha256": WORKFLOW_SHA,
                "runtimeMs": 123,
                "promptId": "prompt-real-fixture",
                "remoteHost": "HARRY-ROG",
                "gpuName": "NVIDIA GeForce GTX 1660 SUPER",
                "vramPeakMb": 4096,
            },
        )


class HealthyWorker:
    def probe(self):
        return WorkerHealth(
            status=WorkerStatus.HEALTHY,
            gpu_name="NVIDIA GeForce GTX 1660 SUPER",
            vram_free_mb=5132,
        )


class DegradedWorker:
    def probe(self):
        return WorkerHealth(status=WorkerStatus.DEGRADED, gpu_name="GTX 1660 SUPER", vram_free_mb=1000)


class RecoveringWorker:
    def __init__(self, recovered: bool):
        self.recovered = recovered
        self.probes = 0
        self.invalidated = 0

    def probe(self):
        self.probes += 1
        return WorkerHealth(
            status=WorkerStatus.HEALTHY if self.recovered and self.probes > 1 else WorkerStatus.DEGRADED,
            gpu_name="GTX 1660 SUPER",
            vram_free_mb=5000 if self.recovered and self.probes > 1 else 1000,
        )

    def invalidate(self):
        self.invalidated += 1


def _smoke(path: Path) -> None:
    path.write_text(json.dumps({
        "branch": "comfyui-remote",
        "status": "PASS",
        "mock_used": False,
        "local_fallback": False,
        "silent_fallback": False,
        "pixelPreservationResult": "PASS",
        "sourceSha256": "a" * 64,
        "a2Sha256": A2_SHA,
        "workflowSha256": WORKFLOW_SHA,
        "outputSha256": "b" * 64,
        "promptId": "prompt-real",
    }), encoding="utf-8")


def test_remote_executor_requires_real_smoke_before_ready(tmp_path: Path) -> None:
    case, base = _case(tmp_path)
    executor = ComfyUIRemoteBenchmarkExecutor(
        FakeRemoteUseCase(tmp_path, base), _command_factory(base, "comfyui-remote"), REPO_ROOT
    )
    capability = executor.capabilities()["comfyui-remote"]
    assert capability["registered"] is True
    assert capability["physicalCallable"] is True
    assert capability["ready"] is False
    with pytest.raises(BenchmarkExecutionError, match="physical smoke"):
        executor.execute(case=case, branch="comfyui-remote", run_id="r", attempt_id="a", seed=42)


def test_bootstrap_smoke_does_not_require_prior_smoke_and_writes_nonbenchmark_evidence(tmp_path: Path) -> None:
    case, base = _case(tmp_path)
    case["id"] = "B01"
    executor = ComfyUIRemoteBenchmarkExecutor(
        FakeRemoteUseCase(tmp_path, base),
        _command_factory(base, "comfyui-remote"),
        REPO_ROOT,
        health=HealthyWorker(),
        evidence_root=tmp_path / "evidence",
    )
    result = executor.execute_bootstrap_smoke(
        case=case, branch="comfyui-remote", run_id="preflight-b01", attempt_id="b01-smoke-1", seed=42
    )
    manifest = Path(result["smokeEvidencePath"])
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["evidenceType"] == "NON_BENCHMARK"
    assert payload["phase"] == "PREFLIGHT"
    assert payload["caseId"] == "B01"
    assert result["executorStatus"] == "COMPLETED"
    official_executor = ComfyUIRemoteBenchmarkExecutor(
        FakeRemoteUseCase(tmp_path, base),
        _command_factory(base, "comfyui-remote"),
        REPO_ROOT,
        physical_smoke_evidence=manifest,
        health=HealthyWorker(),
    )
    assert official_executor.capabilities()["comfyui-remote"]["ready"] is True
    assert official_executor.execute(
        case=case, branch="comfyui-remote", run_id="official", attempt_id="a1", seed=42
    )["executorStatus"] == "COMPLETED"


def test_bootstrap_smoke_rejects_non_b01_case(tmp_path: Path) -> None:
    case, base = _case(tmp_path)
    case["id"] = "B02"
    executor = ComfyUIRemoteBenchmarkExecutor(
        FakeRemoteUseCase(tmp_path, base), _command_factory(base, "comfyui-remote"),
        REPO_ROOT, health=HealthyWorker(), evidence_root=tmp_path / "evidence",
    )
    with pytest.raises(BenchmarkExecutionError, match="restricted to .*B01"):
        executor.execute_bootstrap_smoke(
            case=case, branch="comfyui-remote", run_id="r", attempt_id="a", seed=42
        )


def test_bootstrap_smoke_rejects_failed_vram_health(tmp_path: Path) -> None:
    case, base = _case(tmp_path)
    executor = ComfyUIRemoteBenchmarkExecutor(
        FakeRemoteUseCase(tmp_path, base), _command_factory(base, "comfyui-remote"),
        REPO_ROOT, health=DegradedWorker(), evidence_root=tmp_path / "evidence",
    )
    with pytest.raises(BenchmarkExecutionError, match="DEGRADED"):
        executor.execute_bootstrap_smoke(
            case={**case, "id": "B01"}, branch="comfyui-remote", run_id="r", attempt_id="a", seed=42
        )


def test_low_vram_recovery_releases_once_reprobes_and_allows_execution(tmp_path: Path) -> None:
    case, base = _case(tmp_path)
    smoke = tmp_path / "verification_report.json"
    _smoke(smoke)
    worker = RecoveringWorker(recovered=True)
    releases = []
    executor = ComfyUIRemoteBenchmarkExecutor(
        FakeRemoteUseCase(tmp_path, base), _command_factory(base, "comfyui-remote"), REPO_ROOT,
        smoke, worker, evidence_root=tmp_path / "evidence",
        memory_release=lambda: releases.append({"ok": True}) or {"ok": True},
    )
    evidence = executor.execute(case=case, branch="comfyui-remote", run_id="r", attempt_id="a", seed=42)
    assert evidence["executorStatus"] == "COMPLETED"
    assert releases == [{"ok": True}]
    assert worker.probes == 2
    assert worker.invalidated == 1
    assert evidence["lineage"]["restoration"]["vramRecovery"][0]["afterVramFreeMb"] == 5000


def test_low_vram_recovery_fails_closed_without_prompt_when_still_degraded(tmp_path: Path) -> None:
    case, base = _case(tmp_path)
    smoke = tmp_path / "verification_report.json"
    _smoke(smoke)
    worker = RecoveringWorker(recovered=False)
    executed = []
    use_case = FakeRemoteUseCase(tmp_path, base)
    original = use_case.execute
    use_case.execute = lambda command: executed.append(command) or original(command)
    executor = ComfyUIRemoteBenchmarkExecutor(
        use_case, _command_factory(base, "comfyui-remote"), REPO_ROOT,
        smoke, worker, memory_release=lambda: {"ok": True},
    )
    with pytest.raises(BenchmarkExecutionError, match="DEGRADED"):
        executor.execute(case=case, branch="comfyui-remote", run_id="r", attempt_id="a", seed=42)
    assert worker.probes == 2
    assert executed == []


def test_remote_health_or_fallback_mismatch_keeps_capability_blocked(tmp_path: Path) -> None:
    case, base = _case(tmp_path)
    smoke = tmp_path / "verification_report.json"
    _smoke(smoke)
    payload = json.loads(smoke.read_text(encoding="utf-8"))
    payload["silent_fallback"] = True
    smoke.write_text(json.dumps(payload), encoding="utf-8")
    executor = ComfyUIRemoteBenchmarkExecutor(
        FakeRemoteUseCase(tmp_path, base), _command_factory(base, "comfyui-remote"), REPO_ROOT, smoke, HealthyWorker()
    )
    capability = executor.capabilities()["comfyui-remote"]
    assert capability["ready"] is False
    assert "silent_fallback" in capability["blockers"][0]


def test_remote_executor_uses_existing_use_case_and_emits_evidence(tmp_path: Path) -> None:
    case, base = _case(tmp_path)
    smoke = tmp_path / "verification_report.json"
    _smoke(smoke)
    executor = ComfyUIRemoteBenchmarkExecutor(
        FakeRemoteUseCase(tmp_path, base), _command_factory(base, "comfyui-remote"), REPO_ROOT, smoke, HealthyWorker()
    )
    evidence = executor.execute(case=case, branch="comfyui-remote", run_id="r", attempt_id="a", seed=42)
    assert evidence["executorStatus"] == "COMPLETED"
    assert evidence["providerRequestId"] == "prompt-real-fixture"
    assert evidence["workflowSha256"] == WORKFLOW_SHA
    assert evidence["gpuName"] == "NVIDIA GeForce GTX 1660 SUPER"
    assert evidence["vramPeakMb"] == 4096
    assert evidence["restoredCropSha256"] != hashlib.sha256(base).hexdigest()
    assert "ComfyUIHttpClient" not in inspect.getsource(ComfyUIRemoteBenchmarkExecutor)


def test_remote_evidence_can_validate_against_benchmark_schema(tmp_path: Path) -> None:
    case, base = _case(tmp_path)
    smoke = tmp_path / "verification_report.json"
    _smoke(smoke)
    executor = ComfyUIRemoteBenchmarkExecutor(
        FakeRemoteUseCase(tmp_path, base), _command_factory(base, "comfyui-remote"), REPO_ROOT, smoke, HealthyWorker()
    )
    evidence = executor.execute(case=case, branch="comfyui-remote", run_id="r", attempt_id="a", seed=42)
    row = {
        "benchmarkVersion": "2.1",
        "benchmarkId": case["id"],
        "taxonomy": case["taxonomy"],
        "branch": "comfyui-remote",
        "baseFrameSha256": case["baseFrame"]["sha256"],
        "a2Sha256": A2_SHA,
        "seed": 42,
        "restorerId": "comfyui-remote",
        **{key: None for key in (
            "faceQcBefore", "faceQcAfter", "identityScore", "eyesBrowsScore", "geometryScore",
            "anatomyScore", "outfitScore", "environmentScore", "globalScore",
        )},
        **evidence,
    }
    schema = json.loads((REPO_ROOT / "contracts/identity_restoration/benchmark_row.schema.json").read_text())
    jsonschema.validate(row, schema)


def test_remote_workflow_mismatch_fails_closed(tmp_path: Path) -> None:
    case, base = _case(tmp_path)
    smoke = tmp_path / "verification_report.json"
    _smoke(smoke)

    def wrong_factory(case, run_id, attempt_id, seed):
        command = _command_factory(base, "comfyui-remote")(case, run_id, attempt_id, seed)
        from dataclasses import replace
        return replace(command, workflow_id="wrong-workflow")

    executor = ComfyUIRemoteBenchmarkExecutor(
        FakeRemoteUseCase(tmp_path, base), wrong_factory, REPO_ROOT, smoke, HealthyWorker()
    )
    with pytest.raises(BenchmarkExecutionError, match="workflow ID"):
        executor.execute(case=case, branch="comfyui-remote", run_id="r", attempt_id="a", seed=42)


def test_local_and_remote_request_factories_preserve_geometry_inputs(tmp_path: Path) -> None:
    case, base = _case(tmp_path)
    local = _command_factory(base, "comfyui-local")(case, "r", "local", 42)
    remote = _command_factory(base, "comfyui-remote")(case, "r", "remote", 42)
    assert hashlib.sha256(local.crop_png).hexdigest() == hashlib.sha256(remote.crop_png).hexdigest()
    assert local.mask.editable == remote.mask.editable
    assert local.full_canvas_mask.editable == remote.full_canvas_mask.editable
    assert local.crop_transform == remote.crop_transform
    assert local.a2_sha256 == remote.a2_sha256 == A2_SHA
    assert local.seed == remote.seed == 42


def test_cli_has_no_force_bypass_and_executor_has_no_http_transport() -> None:
    from identity_restoration.interface import cli
    assert "--force" not in inspect.getsource(cli)
    assert "ComfyUIHttpClient" not in inspect.getsource(ComfyUIRemoteBenchmarkExecutor)
