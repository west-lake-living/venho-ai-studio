from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from identity_restoration.domain.entities import A2Authority, MaskSet, RestorationRequest
from identity_restoration.domain.errors import RestorationError
from identity_restoration.domain.value_objects import RestorationParams
from identity_restoration.infrastructure.comfyui.http_client import UploadedRef
from identity_restoration.infrastructure.restorers.comfyui_candidate_v3_adapter import (
    CANDIDATE_V3_PROFILE_ID,
    CANDIDATE_V3_WORKFLOW_ID,
    ComfyUiCandidateV3Adapter,
)


ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = json.loads(
    (ROOT / "identity_restoration/workflows/face_restore_win_sd15_ipadapter_v3.api.json").read_text()
)


def _png(size: tuple[int, int], mode: str, value: int | tuple[int, ...]) -> bytes:
    image = Image.new(mode, size, value)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


class FakeBackend:
    def __init__(self, output: bytes) -> None:
        self.output = output
        self.uploads: list[str] = []
        self.submitted: list[dict] = []

    def upload_image(self, data: bytes, filename: str, *, run_id: str, attempt_id: str) -> UploadedRef:
        self.uploads.append(filename)
        return UploadedRef(filename, f"venho/{run_id}/{attempt_id}", "input")

    def submit_prompt(self, workflow: dict) -> str:
        self.submitted.append(workflow)
        return "prompt-test"

    def poll_until_complete(self, prompt_id: str, *, timeout_seconds: float) -> dict:
        return {"filename": "restored.png", "subfolder": "", "type": "output"}

    def download(self, image_info: dict) -> bytes:
        return self.output


def _request(*, crop: bytes | None = None, mask: bytes | None = None) -> RestorationRequest:
    return RestorationRequest(
        run_id="run-1",
        attempt_id="attempt-1",
        crop_png=crop or _png((512, 512), "RGB", (10, 20, 30)),
        mask=MaskSet(
            editable=mask or _png((512, 512), "L", 255),
            feather=_png((512, 512), "L", 255),
            version="candidate_v3_mask_v1",
        ),
        a2=A2Authority.from_bytes(_png((512, 512), "RGB", (1, 2, 3))),
        workflow_id=CANDIDATE_V3_WORKFLOW_ID,
        seed=42,
        params=RestorationParams(denoise=0.35, steps=20, cfg=6.0, sampler="euler", scheduler="normal"),
    )


def _adapter(backend: FakeBackend, **kwargs) -> ComfyUiCandidateV3Adapter:
    workflow = kwargs.pop("workflow", WORKFLOW)
    return ComfyUiCandidateV3Adapter(
        client=backend,
        workflow=workflow,
        workflow_sha256="a" * 64,
        model_identifiers=("checkpoint", "faceid"),
        **kwargs,
    )


def test_candidate_v3_requires_explicit_gpu_authorization_before_upload() -> None:
    backend = FakeBackend(_png((512, 512), "RGB", (40, 50, 60)))

    with pytest.raises(RestorationError, match="GPU_NOT_AUTHORIZED"):
        _adapter(backend).restore(_request())

    assert backend.uploads == []


def test_candidate_v3_binds_declared_graph_and_returns_lineage() -> None:
    backend = FakeBackend(_png((512, 512), "RGB", (40, 50, 60)))
    adapter = _adapter(
        backend,
        gpu_execution_authorized=True,
        gpu_evidence={"gpuName": "fixture-gpu", "vramFreeMb": 5000},
    )

    restored = adapter.restore(_request())
    evidence = adapter.execution_evidence()

    assert (restored.width, restored.height) == (512, 512)
    assert len(backend.uploads) == 3
    assert len(backend.submitted) == 1
    assert evidence["candidateProfileId"] == CANDIDATE_V3_PROFILE_ID
    assert evidence["workflowSha256"] == "a" * 64
    assert evidence["selectedReferenceHashes"] == [_request().a2.sha256]
    assert evidence["modelIdentifiers"] == ["checkpoint", "faceid"]
    assert evidence["gpuEvidence"]["gpuName"] == "fixture-gpu"
    assert evidence["outputGeometry"] == {"width": 512, "height": 512}


def test_candidate_v3_rejects_noncanonical_geometry_before_upload() -> None:
    backend = FakeBackend(_png((512, 512), "RGB", (40, 50, 60)))

    with pytest.raises(RestorationError, match="GEOMETRY_MISMATCH"):
        _adapter(backend, gpu_execution_authorized=True).restore(
            _request(crop=_png((256, 256), "RGB", (10, 20, 30)))
        )

    assert backend.uploads == []


def test_candidate_v3_rejects_graph_contract_before_upload() -> None:
    backend = FakeBackend(_png((512, 512), "RGB", (40, 50, 60)))
    broken = json.loads(json.dumps(WORKFLOW))
    broken["12"]["class_type"] = "WrongSampler"

    with pytest.raises(RestorationError, match="NODE_BINDING_FAILED"):
        _adapter(backend, workflow=broken, gpu_execution_authorized=True).restore(_request())

    assert backend.uploads == []
