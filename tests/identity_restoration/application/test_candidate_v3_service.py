from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from identity_restoration.application.candidate_v3_service import (
    CandidateV3ApiBoundary,
    CandidateV3BridgeResult,
    CandidateV3JobRequest,
    CandidateV3RestorationService,
    CandidateV3ServiceError,
)
from identity_restoration.application.face_observability import FaceDetection, FaceObservabilityConfig, FaceObservabilityService
from identity_restoration.application.identity_pack import FaceBounds, IdentityPack, IdentityPose, IdentityReference


def _png(size=(256, 256), mode="RGB", color=None):
    color = color if color is not None else ((20, 30, 40) if mode == "RGB" else 255)
    out = io.BytesIO()
    Image.new(mode, size, color).save(out, format="PNG")
    return out.getvalue()


def _pack() -> IdentityPack:
    reference = IdentityReference(
        reference_id="A2_FRONT",
        artifact_path="assets/A2_Front.png",
        artifact_sha256="a" * 64,
        role="PRIMARY_FRONTAL",
        pose=IdentityPose(0, 0, 0, 10),
        face_bounds=FaceBounds(1, 1, 2, 2),
        usable_regions=("eyes", "nose", "mouth"),
        consent_or_authority_ref="approved",
        approved=True,
    )
    return IdentityPack("1.0", "pack-v1", "linh-an", "APPROVED", (reference,), "b" * 64, "2026-08-27", "Harry Pham")


@dataclass
class PackRepo:
    pack: IdentityPack | None = _pack()

    def get_approved(self, _pack_id):
        if self.pack is None:
            raise ValueError("missing pack")
        return self.pack

    def get(self, pack_id):
        return self.get_approved(pack_id)


class FakeBridge:
    def __init__(self, *, fail=False):
        self.calls = 0
        self.fail = fail

    def execute(self, request):
        self.calls += 1
        if self.fail:
            raise CandidateV3ServiceError("BRIDGE_OUTPUT_INVALID")
        return CandidateV3BridgeResult(_png((512, 512), color=(20, 30, 40)), {"workflowSha256": "53dc090691b8feac2a8b8a4309d43af737e304b09330e072b4ab5632ed5aad91", "attemptId": request.attempt_id})


class Detector:
    def __init__(self, bbox=(65, 65, 190, 190)):
        self.bbox = bbox

    def detect(self, _image):
        left, top, right, bottom = self.bbox
        width, height = right - left, bottom - top
        return (FaceDetection(0.95, self.bbox, ((left + width * 0.3, top + height * 0.3), (left + width * 0.7, top + height * 0.3), ((left + right) / 2, (top + bottom) / 2), (left + width * 0.35, top + height * 0.75), (left + width * 0.65, top + height * 0.75)), 0, 0, 0),)


def _service(tmp_path: Path, bridge=None, *, bbox=(65, 65, 190, 190), pack=None, missing_pack=False, enabled=True):
    config = FaceObservabilityConfig("detector", "1", "d" * 64, "e" * 64, 0.6)
    return CandidateV3RestorationService(
        enabled=enabled,
        artifact_root=tmp_path,
        identity_packs=PackRepo(None if missing_pack else (pack or _pack())),
        observability=FaceObservabilityService(Detector(bbox), config),
        bridge=bridge or FakeBridge(),
        scenario_resolver=lambda scenario: {"bindingId": scenario, "sha256": "f" * 64},
        scenario_validator=lambda _binding, _image: True,
        face_qc=lambda _canonical, _refs: 95.0,
    )


def _request(job_id="job-1", attempt_id="attempt-1"):
    image = _png()
    mask_array = np.zeros((256, 256), dtype=np.uint8)
    mask_array[45:210, 45:210] = 255
    mask_out = io.BytesIO()
    Image.fromarray(mask_array).save(mask_out, format="PNG")
    mask = mask_out.getvalue()
    return CandidateV3JobRequest(job_id, "run-1", attempt_id, "pack-v1", "B05", image, mask, mask, image, seed=7)


def test_phase5_eligible_flow_is_mocked_and_persists_manifest(tmp_path):
    bridge = FakeBridge()
    service = _service(tmp_path, bridge)
    submitted = service.submit(_request())
    result = service.run(submitted["jobId"])
    assert result["status"] == "COMPLETED"
    assert result["route"] == "ELIGIBLE"
    assert result["qualityStatus"] == "PASS"
    assert bridge.calls == 1
    assert Path(result["manifest"]["path"]).is_file()


def test_microface_route_does_not_call_bridge(tmp_path):
    bridge = FakeBridge()
    service = _service(tmp_path, bridge, bbox=(100, 100, 110, 110))
    result = service.run(service.submit(_request())["jobId"])
    assert result["status"] == "BASE_REGEN_REQUIRED"
    assert bridge.calls == 0


def test_invalid_identity_authority_fails_before_bridge(tmp_path):
    bridge = FakeBridge()
    service = _service(tmp_path, bridge, missing_pack=True)
    result = service.run(service.submit(_request())["jobId"])
    assert result["status"] == "FAILED"
    assert result["error"] == "IDENTITY_AUTHORITY_INVALID"
    assert bridge.calls == 0


def test_cancellation_and_duplicate_retry_are_explicit(tmp_path):
    bridge = FakeBridge()
    service = _service(tmp_path, bridge)
    request = _request()
    first = service.submit(request)
    assert service.submit(request) == first
    cancelled = service.cancel(request.job_id)
    assert cancelled["status"] == "CANCELLED"
    assert service.run(request.job_id)["status"] == "CANCELLED"
    retried = service.retry(request.job_id, attempt_id="attempt-2")
    assert retried["status"] == "QUEUED"
    assert service.run(request.job_id)["status"] == "COMPLETED"
    assert bridge.calls == 1


def test_orphaned_job_is_recovered_and_api_is_authorized_and_redacted(tmp_path):
    service = _service(tmp_path)
    request = _request("job-orphan")
    service.submit(request)
    record = service.jobs.get(request.job_id)
    record.update({"status": "RUNNING", "startedAt": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()})
    service.jobs.save(record)
    recovered = service.recover_orphaned(max_runtime_seconds=30)
    assert recovered[0]["status"] == "ORPHANED"

    api = CandidateV3ApiBoundary(service, token="secret")
    with pytest.raises(CandidateV3ServiceError, match="UNAUTHORIZED"):
        api.handle("submit", {"request": request}, authorization="Bearer wrong")
    public = api.handle("submit", {"request": request}, authorization="Bearer secret")
    assert public["jobId"] == request.job_id
    assert not any("path" in key.lower() or "sha" in key.lower() for key in public)
    with pytest.raises(CandidateV3ServiceError, match="PROMOTION_NOT_AUTHORIZED"):
        api.handle("approve", {"jobId": request.job_id}, authorization="Bearer secret")
