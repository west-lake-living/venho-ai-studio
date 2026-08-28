"""Infrastructure composition for the explicitly authorized Phase 7 path."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from ...application.candidate_v3_service import V3_WORKFLOW_SHA256
from ...application.face_observability import FaceObservabilityService
from ...application.phase7_candidate_v3_evaluation import (
    ComfyUiCandidateV3EvaluationBridge,
    Phase7CandidateV3EvaluationEntrypoint,
    Phase7EvaluationError,
    _build_entrypoint,
)
from ..comfyui.http_client import ComfyUIHttpClient
from ..comfyui.workflow_repository import FileWorkflowRepository
from ..face_observability_yunet import PINNED_YUNET_OBSERVABILITY_CONFIG, YuNetFaceDetector
from ..persistence.file_identity_pack_repository import FileIdentityPackRepository
from ..restorers.comfyui_candidate_v3_adapter import (
    CANDIDATE_V3_WORKFLOW_ID,
    ComfyUiCandidateV3Adapter,
)


def build_phase7_candidate_v3_evaluation_entrypoint(
    *,
    repo_root: Path,
    artifact_root: Path,
    worker_base_url: str,
    worker_timeout_seconds: float = 600.0,
    gpu_evidence: Mapping[str, Any] | None = None,
) -> Phase7CandidateV3EvaluationEntrypoint:
    """Build the dedicated evaluation path without touching production registry."""
    workflow_repo = FileWorkflowRepository(
        workflow_root=repo_root / "identity_restoration/workflows",
        pins_path=repo_root / "config/projects/venho_hotel/identity_restoration/workflow_pins.yaml",
    )
    workflow, descriptor = workflow_repo.load(CANDIDATE_V3_WORKFLOW_ID)
    if descriptor.sha256 != V3_WORKFLOW_SHA256:
        raise Phase7EvaluationError("WORKFLOW_AUTHORITY_INVALID")
    adapter = ComfyUiCandidateV3Adapter(
        client=ComfyUIHttpClient(base_url=worker_base_url, timeout_s=worker_timeout_seconds),
        workflow=workflow,
        workflow_id=descriptor.workflow_id,
        workflow_sha256=descriptor.sha256,
        model_identifiers=descriptor.models,
        timeout_seconds=worker_timeout_seconds,
        gpu_execution_authorized=True,
        gpu_evidence=dict(gpu_evidence or {}),
    )
    identity_packs = FileIdentityPackRepository(repo_root)
    bridge = ComfyUiCandidateV3EvaluationBridge(adapter=adapter, identity_packs=identity_packs)
    observability = FaceObservabilityService(
        detector=YuNetFaceDetector(
            model_path=repo_root / "models/geometry/yunet/face_detection_yunet_2023mar.onnx"
        ),
        config=PINNED_YUNET_OBSERVABILITY_CONFIG,
    )
    return _build_entrypoint(
        artifact_root=artifact_root,
        bridge=bridge,
        observability=observability,
        identity_packs=identity_packs,
    )
