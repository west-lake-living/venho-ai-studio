from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
import json
from PIL import Image

from identity_restoration.application.benchmark_executor import (
    NanoBananaEditBenchmarkExecutor,
    NanoBananaEditRequest,
    NanoBananaEditResult,
)
from identity_restoration.application.benchmark_contract import load_benchmark_manifest
from identity_restoration.application.benchmark_runner import BenchmarkExecutionError
from identity_restoration.application.benchmark_geometry import build_frozen_b01_nano_request


REPO_ROOT = Path(__file__).resolve().parents[3]
A2 = REPO_ROOT / "staging/gw-p3/mac-final-20260824-dual-mask/evidence/input_a2.png"
MANIFEST = REPO_ROOT / "contracts/identity_restoration/benchmark_set.yaml"
GEOMETRY = REPO_ROOT / "artifacts/identity-restoration/benchmark-geometry/v2.1/B01/geometry_manifest.json"


def _png(color: tuple[int, int, int]) -> bytes:
    stream = BytesIO()
    Image.new("RGB", (8, 8), color).save(stream, format="PNG")
    return stream.getvalue()


class FakeNanoPath:
    def __init__(self, output: bytes | None = None, *, fail: Exception | None = None):
        self.output = output
        self.fail = fail
        self.requests: list[NanoBananaEditRequest] = []

    def capabilities(self):
        return {
            "ready": True,
            "providerConfigured": True,
            "fallbackEnabled": False,
            "provider": "nano-banana-2",
            "model": "gemini-3.1-flash-image",
            "adapterPath": "existing-production-path",
            "blockers": [],
        }

    def masked_edit(self, request, *, run_id, attempt_id):
        self.requests.append(request)
        if self.fail:
            raise self.fail
        return NanoBananaEditResult(
            image_bytes=self.output or _png((99, 88, 77)),
            provider_id="nano-banana-2",
            model_id="gemini-3.1-flash-image",
            provider_request_id="provider-request-1",
            provider_run_id="provider-run-1",
            runtime_ms=123,
            retry_count=0,
            seed_supported=False,
            backend="gemini-interactions",
            host={"service": "venho-os"},
            mock_used=False,
            local_fallback=False,
            silent_fallback=False,
        )


def _case(tmp_path: Path):
    manifest = load_benchmark_manifest(MANIFEST)
    case = next(item for item in manifest["cases"] if item["id"] == "B01")
    return case, Path(case["baseFrame"]["path"])


def _factory(case, run_id, attempt_id, seed):
    return build_frozen_b01_nano_request(
        case,
        geometry_authority_path=GEOMETRY,
        canonical_a2_path=A2,
        run_id=run_id,
        attempt_id=attempt_id,
        seed=seed,
    )


def test_executor_wraps_existing_path_and_records_truthful_evidence(tmp_path: Path):
    path = FakeNanoPath()
    executor = NanoBananaEditBenchmarkExecutor(
        path, _factory, canonical_a2_path=A2, evidence_root=tmp_path / "evidence"
    )
    case, _ = _case(tmp_path)

    evidence = executor.execute(
        case=case, branch="nano-banana-edit", run_id="r1", attempt_id="a1", seed=42
    )

    assert len(path.requests) == 1
    assert evidence["provider"] == "nano-banana-2"
    assert evidence["model"] == "gemini-3.1-flash-image"
    assert evidence["operation"] == "masked_edit"
    assert evidence["seedSupported"] is False
    assert evidence["outputSha256"] != case["baseFrame"]["sha256"]
    assert Path(evidence["outputPath"]).is_file()
    assert Path(evidence["evidencePath"]).is_file()


def test_executor_rejects_provider_failure_and_retains_failure_evidence(tmp_path: Path):
    path = FakeNanoPath(fail=RuntimeError("provider unavailable"))
    executor = NanoBananaEditBenchmarkExecutor(
        path, _factory, canonical_a2_path=A2, evidence_root=tmp_path / "evidence"
    )
    case, _ = _case(tmp_path)

    with pytest.raises(BenchmarkExecutionError, match="provider execution failed"):
        executor.execute(case=case, branch="nano-banana-edit", run_id="r1", attempt_id="a1", seed=42)
    assert (tmp_path / "evidence/r1/a1/failure.json").is_file()


def test_executor_rejects_fallback_and_wrong_authority(tmp_path: Path):
    path = FakeNanoPath()
    executor = NanoBananaEditBenchmarkExecutor(
        path, _factory, canonical_a2_path=A2, evidence_root=tmp_path / "evidence"
    )
    case, base = _case(tmp_path)
    case["baseFrame"]["sha256"] = "0" * 64

    with pytest.raises(BenchmarkExecutionError, match="base frame SHA-256 mismatch"):
        executor.execute(case=case, branch="nano-banana-edit", run_id="r1", attempt_id="a1", seed=42)

    assert executor.capabilities()["nano-banana-edit"]["ready"] is True


def test_executor_rejects_wrong_frozen_mask_before_provider_call(tmp_path: Path):
    path = FakeNanoPath()

    def bad_factory(case, run_id, attempt_id, seed):
        request = _factory(case, run_id, attempt_id, seed)
        return request.__class__(
            **{
                **request.__dict__,
                "mask_path": GEOMETRY.with_name("missing-mask.png"),
            }
        )

    executor = NanoBananaEditBenchmarkExecutor(
        path, bad_factory, canonical_a2_path=A2, evidence_root=tmp_path / "evidence"
    )
    case, _ = _case(tmp_path)

    with pytest.raises(BenchmarkExecutionError, match="frozen geometry validation failed"):
        executor.execute(case=case, branch="nano-banana-edit", run_id="r1", attempt_id="a1", seed=42)
    assert path.requests == []


def test_executor_has_no_generation_pipeline_or_vendor_client():
    from identity_restoration.application import benchmark_executor

    source = Path(benchmark_executor.__file__).read_text(encoding="utf-8")
    assert "ActionCompositePipeline(" not in source
    assert "GoogleGenAI" not in source
    assert "GeminiImageProvider" not in source


def test_executor_reuses_verified_artifact_without_provider_recall(tmp_path: Path):
    output = tmp_path / "reused.png"
    output.write_bytes(_png((9, 8, 7)))
    evidence_path = tmp_path / "prior-evidence.json"
    import hashlib
    evidence_path.write_text(json.dumps({
        "executorStatus": "COMPLETED",
        "outputPath": str(output),
        "outputSha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "provider": "nano-banana-2",
        "model": "gemini-3.1-flash-image",
        "lineage": {},
    }), encoding="utf-8")
    path = FakeNanoPath(fail=AssertionError("provider must not be called"))
    executor = NanoBananaEditBenchmarkExecutor(
        path, _factory, canonical_a2_path=A2, evidence_root=tmp_path / "evidence",
        reusable_evidence={"B01": evidence_path},
    )
    case, _ = _case(tmp_path)
    result = executor.execute(case=case, branch="nano-banana-edit", run_id="new", attempt_id="a1", seed=42)
    assert result["lineage"]["artifactReuse"]["providerCallReused"] is True
    assert path.requests == []
