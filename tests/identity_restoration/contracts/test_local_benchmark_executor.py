from __future__ import annotations

import hashlib
import inspect
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from identity_restoration.application.benchmark_executor import (
    ComfyUILocalBenchmarkExecutor,
)
from identity_restoration.application.benchmark_runner import BenchmarkExecutionError
from identity_restoration.application.dto.restore_command import RestoreCommand
from identity_restoration.application.dto.restoration_result import RestorationResult
from identity_restoration.application.ports.identity_restorer import RestorerDescriptor
from identity_restoration.application.registry.restorer_registry import RestorerRegistry
from identity_restoration.application.use_cases.restore_face_crop import RestoreFaceCropUseCase
from identity_restoration.domain.entities import A2Authority, CropTransform, MaskSet, RestoredCrop
from identity_restoration.domain.value_objects import RestorationParams
from identity_restoration.infrastructure.persistence.atomic_file_artifact_sink import AtomicFileArtifactSink
from identity_restoration.infrastructure.persistence.file_concurrency_lease import FileConcurrencyLease
from identity_restoration.infrastructure.persistence.jsonl_restoration_ledger import JsonlRestorationLedger
from identity_restoration.infrastructure.system.system_clock import SystemClock
from identity_restoration.interface.cli import main


REPO_ROOT = Path(__file__).resolve().parents[3]
A2_SHA = "1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d"
LOCAL_WORKFLOW_SHA = "b232b18d498f9a0064707a83aeebb36306fda147ac50d757a27721267c9f3e25"


class FakeA2Repository:
    path = "/canonical/A2_Front_plate.png"

    def load(self):
        return A2Authority(image_bytes=b"canonical-a2", sha256=A2_SHA)


class TrackingLocalRestorer:
    restorer_id = "comfyui-local"

    def __init__(self):
        self.requests = []

    def restore(self, request):
        self.requests.append(request)
        image = Image.open(BytesIO(request.crop_png)).convert("RGBA")
        pixel = image.getpixel((0, 0))
        image.putpixel((0, 0), (min(pixel[0] + 1, 255), pixel[1], pixel[2], pixel[3]))
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return RestoredCrop.from_png_bytes(buffer.getvalue())

    def describe(self):
        return RestorerDescriptor(
            restorer_id="comfyui-local",
            workflow_id="face_restore_v1_api",
            workflow_sha256=LOCAL_WORKFLOW_SHA,
        )


def _png(size=(8, 8), color=(20, 30, 40, 255)) -> bytes:
    buffer = BytesIO()
    Image.new("RGBA", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


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


def _command_factory(base_png: bytes):
    def factory(case, run_id, attempt_id, seed):
        mask = _png(color=(255, 255, 255, 255))
        return RestoreCommand(
            run_id=run_id,
            attempt_id=attempt_id,
            restorer_id="comfyui-local",
            crop_png=base_png,
            mask=MaskSet(editable=mask, feather=mask, version="test-mask-v1"),
            full_canvas_mask=MaskSet(editable=mask, feather=mask, version="test-full-mask-v1"),
            base_canvas_png=base_png,
            crop_transform=CropTransform.from_box(0, 0, 8, 8, 8),
            a2_path="/canonical/A2_Front_plate.png",
            a2_sha256=A2_SHA,
            workflow_id="face_restore_v1_api",
            seed=seed,
            params=RestorationParams(denoise=0.35, steps=20, cfg=6.0, sampler="euler", scheduler="normal"),
        )

    return factory


def _executor(tmp_path: Path, restorer=None) -> tuple[ComfyUILocalBenchmarkExecutor, object]:
    restorer = restorer or TrackingLocalRestorer()
    use_case = RestoreFaceCropUseCase(
        registry=RestorerRegistry(restorers={"comfyui-local": restorer}, default_id="comfyui-local"),
        a2_authority=FakeA2Repository(),
        artifact_sink=AtomicFileArtifactSink(tmp_path / "artifacts"),
        ledger=JsonlRestorationLedger(tmp_path / "ledger.jsonl"),
        lease=FileConcurrencyLease(tmp_path / "worker.lock"),
        clock=SystemClock(),
    )
    case, base = _case(tmp_path)
    return ComfyUILocalBenchmarkExecutor(use_case, _command_factory(base), REPO_ROOT), restorer


def test_local_executor_wraps_existing_use_case_and_emits_complete_evidence(tmp_path: Path) -> None:
    executor, restorer = _executor(tmp_path)
    case, _ = _case(tmp_path)
    evidence = executor.execute(
        case=case, branch="comfyui-local", run_id="smoke-local", attempt_id="a1", seed=42
    )
    assert len(restorer.requests) == 1
    assert restorer.requests[0].seed == 42
    assert evidence["executorStatus"] == "COMPLETED"
    assert evidence["outputPath"]
    assert len(evidence["outputSha256"]) == 64
    assert evidence["workflowId"] == "face_restore_v1_api"
    assert evidence["workflowSha256"] == LOCAL_WORKFLOW_SHA
    assert evidence["a2Path"] == "/canonical/A2_Front_plate.png"
    assert evidence["cropTransform"]["box"] == [0, 0, 8, 8]
    assert evidence["maskVersion"] == "test-mask-v1"
    assert evidence["pixelPreservationResult"] == "PASS"
    assert "ComfyUIHttpClient" not in inspect.getsource(ComfyUILocalBenchmarkExecutor)


def test_local_capability_and_validated_physical_branches_are_ready(capsys) -> None:
    assert main(["benchmark", "preflight"]) == 0
    result = __import__("json").loads(capsys.readouterr().out)
    branches = {branch["branch"]: branch for branch in result["branches"]}
    assert branches["comfyui-local"]["ready"] is True
    assert branches["comfyui-remote"]["ready"] is True
    assert branches["nano-banana-edit"]["ready"] is True
    assert result["officialExecutionReady"] is True


def test_missing_output_is_retained_as_failure(tmp_path: Path) -> None:
    class MissingOutputUseCase:
        def execute(self, command):
            return RestorationResult(run_id=command.run_id, attempt_id=command.attempt_id, status="NEEDS_REVIEW")

    case, base = _case(tmp_path)
    executor = ComfyUILocalBenchmarkExecutor(MissingOutputUseCase(), _command_factory(base), REPO_ROOT)
    with pytest.raises(BenchmarkExecutionError, match="no composite output path"):
        executor.execute(case=case, branch="comfyui-local", run_id="r", attempt_id="a", seed=42)


def test_restoration_exception_is_retained_as_failure(tmp_path: Path) -> None:
    class ExplodingUseCase:
        def execute(self, command):
            raise RuntimeError("worker unavailable")

    case, base = _case(tmp_path)
    executor = ComfyUILocalBenchmarkExecutor(ExplodingUseCase(), _command_factory(base), REPO_ROOT)
    with pytest.raises(BenchmarkExecutionError, match="worker unavailable"):
        executor.execute(case=case, branch="comfyui-local", run_id="r", attempt_id="a", seed=42)


def test_malformed_result_is_rejected(tmp_path: Path) -> None:
    class MalformedUseCase:
        def execute(self, command):
            return {"status": "NEEDS_REVIEW"}

    case, base = _case(tmp_path)
    executor = ComfyUILocalBenchmarkExecutor(MalformedUseCase(), _command_factory(base), REPO_ROOT)
    with pytest.raises(BenchmarkExecutionError, match="malformed result"):
        executor.execute(case=case, branch="comfyui-local", run_id="r", attempt_id="a", seed=42)
