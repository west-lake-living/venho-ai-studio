from __future__ import annotations

import io
import hashlib
from pathlib import Path

import pytest
from PIL import Image

from identity_restoration.application.candidate_v3_service import CandidateV3BridgeResult, CandidateV3JobRequest
from identity_restoration.application.dto.candidate_v3 import ArtifactRef, CandidateV3Request
from identity_restoration.application.phase7_candidate_v3_evaluation import (
    BENCHMARK_BRANCH,
    PHASE_7_EVALUATION_PURPOSE,
    Phase7CandidateV3EvaluationEntrypoint,
    Phase7EvaluationError,
    _scenario_bindings,
    ComfyUiCandidateV3EvaluationBridge,
)
from identity_restoration.domain.entities import RestoredCrop


def _png(size=(512, 512), color=(30, 40, 50)) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", size, color).save(output, format="PNG")
    return output.getvalue()


class Service:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def submit(self, request: CandidateV3JobRequest):
        self.calls.append(f"submit:{request.job_id}")
        return {"jobId": request.job_id}

    def run(self, job_id: str):
        self.calls.append(f"run:{job_id}")
        return {"status": "COMPLETED", "jobId": job_id}


def _request(tmp_path: Path) -> CandidateV3Request:
    image = _png()
    paths = []
    for name, data in (("image.png", image), ("editable.png", image), ("feather.png", image), ("a2.png", image)):
        path = tmp_path / name
        path.write_bytes(data)
        paths.append(ArtifactRef(str(path), hashlib.sha256(data).hexdigest(), 512, 512, "image/png"))
    return CandidateV3Request(
        contract_version="1.0",
        run_id="run-1",
        attempt_id="attempt-1",
        canonical_image=paths[0],
        canonical_editable_mask=paths[1],
        canonical_feather_mask=paths[2],
        transform=None,  # type: ignore[arg-type]
        selected_identity_references=(paths[3],),
        candidate_profile_id="candidate-v3-sd15-faceid-canonical-512",
        seed=42,
        effective_config_sha256="",
        timeout_seconds=600,
    )


class Adapter:
    def __init__(self) -> None:
        self.request = None

    def restore(self, request):
        self.request = request
        return RestoredCrop(_png(), 512, 512)

    def execution_evidence(self):
        return {"workflowSha256": "53dc090691b8feac2a8b8a4309d43af737e304b09330e072b4ab5632ed5aad91"}


def test_evaluation_entrypoint_requires_exact_purpose() -> None:
    service = Service()
    entrypoint = Phase7CandidateV3EvaluationEntrypoint(service)  # type: ignore[arg-type]
    with pytest.raises(Phase7EvaluationError, match="PURPOSE_REQUIRED"):
        entrypoint.evaluate(object(), purpose=None)  # type: ignore[arg-type]
    with pytest.raises(Phase7EvaluationError, match="PURPOSE_REQUIRED"):
        entrypoint.evaluate(object(), purpose="PRODUCTION")  # type: ignore[arg-type]
    assert service.calls == []


def test_evaluation_entrypoint_is_terminal_evaluation_only() -> None:
    service = Service()
    entrypoint = Phase7CandidateV3EvaluationEntrypoint(service)  # type: ignore[arg-type]
    request = CandidateV3JobRequest(
        "job-1", "run-1", "attempt-1", "pack", "B01", b"image", b"mask", b"mask", b"base"
    )
    result = entrypoint.evaluate(request, purpose=PHASE_7_EVALUATION_PURPOSE)
    assert service.calls == ["submit:job-1", "run:job-1"]
    assert result["evaluation"] == {
        "purpose": PHASE_7_EVALUATION_PURPOSE,
        "benchmarkBranch": BENCHMARK_BRANCH,
        "evaluationOnly": True,
        "productionEligible": False,
        "featureFlag": "OFF",
    }


def test_bridge_verifies_artifacts_and_calls_existing_adapter(tmp_path: Path) -> None:
    adapter = Adapter()
    bridge = ComfyUiCandidateV3EvaluationBridge(adapter=adapter, identity_packs=object())  # type: ignore[arg-type]
    result = bridge.execute(_request(tmp_path))
    assert result.lineage["evaluationPurpose"] == PHASE_7_EVALUATION_PURPOSE
    assert result.lineage["productionEligible"] is False
    assert adapter.request.workflow_id == "face_restore_win_sd15_ipadapter_v3"
    assert adapter.request.seed == 42
    assert adapter.request.params.steps == 20


def test_bridge_rejects_mismatched_reference_hash(tmp_path: Path) -> None:
    adapter = Adapter()
    bridge = ComfyUiCandidateV3EvaluationBridge(adapter=adapter, identity_packs=object())  # type: ignore[arg-type]
    request = _request(tmp_path)
    bad_ref = ArtifactRef(request.selected_identity_references[0].path, "0" * 64, 512, 512, "image/png")
    request = CandidateV3Request(
        contract_version=request.contract_version,
        run_id=request.run_id,
        attempt_id=request.attempt_id,
        canonical_image=request.canonical_image,
        canonical_editable_mask=request.canonical_editable_mask,
        canonical_feather_mask=request.canonical_feather_mask,
        transform=request.transform,
        selected_identity_references=(bad_ref,),
        candidate_profile_id=request.candidate_profile_id,
        seed=request.seed,
        effective_config_sha256=request.effective_config_sha256,
        timeout_seconds=request.timeout_seconds,
    )
    with pytest.raises(Phase7EvaluationError, match="HASH_MISMATCH"):
        bridge.execute(request)
    assert adapter.request is None


def test_scenario_bindings_match_authoritative_ids() -> None:
    bindings = _scenario_bindings()
    assert bindings["B01"]["bindingId"] == "candidate-v3-B01-canonical-default-v1"
    assert bindings["B03"]["bindingId"] == "candidate-v3-B03-action-full-body-1-0-v1"
    assert bindings["B03"]["allowedExclusions"] == ["shot_distance", "hairstyle"]
