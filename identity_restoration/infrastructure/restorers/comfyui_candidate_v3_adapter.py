from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from io import BytesIO
from typing import Any, Mapping, Protocol

from PIL import Image

from ...application.ports.identity_restorer import RestorerDescriptor
from ...domain.entities import RestorationRequest, RestoredCrop
from ...domain.errors import RestorationError
from ...domain.policies.candidate_v3_winning_config import resolve_candidate_v3_params
from ...domain.value_objects import RestorerId
from ..comfyui.graph_binder import bind_candidate_v3_by_title, validate_candidate_v3_graph
from ..comfyui.http_client import ComfyUIHttpClient
from ..comfyui.node_registry import NODE_TITLES


CANDIDATE_V3_WORKFLOW_ID = "face_restore_win_sd15_ipadapter_v3"
CANDIDATE_V3_PROFILE_ID = "candidate_v3"
CANONICAL_SIZE = (512, 512)


class CandidateV3BackendPort(Protocol):
    def upload_image(self, data: bytes, filename: str, *, run_id: str, attempt_id: str): ...

    def submit_prompt(self, workflow: Mapping[str, Any]) -> str: ...

    def poll_until_complete(self, prompt_id: str, *, timeout_seconds: float) -> Mapping[str, Any]: ...

    def download(self, image_info: Mapping[str, Any]) -> bytes: ...


@dataclass
class ComfyUiCandidateV3Adapter:
    """Candidate v3 ComfyUI adapter with a strict, opt-in GPU boundary.

    The adapter implements the existing IdentityRestorerPort so the registry
    remains the only selection boundary. It never executes unless the caller
    explicitly authorizes GPU execution; normal composition leaves that flag
    false. All graph validation happens before the first upload.
    """

    client: CandidateV3BackendPort | ComfyUIHttpClient
    workflow: dict[str, Any]
    workflow_id: str = CANDIDATE_V3_WORKFLOW_ID
    workflow_sha256: str = ""
    model_identifiers: tuple[str, ...] = ()
    timeout_seconds: float = 600.0
    gpu_execution_authorized: bool = False
    gpu_evidence: Mapping[str, Any] | None = None
    restorer_id: RestorerId = "comfyui-candidate-v3"
    candidate_profile_id: str = CANDIDATE_V3_PROFILE_ID
    _last_execution_evidence: dict[str, Any] = field(default_factory=dict, init=False, repr=False)

    def restore(self, request: RestorationRequest) -> RestoredCrop:
        self._last_execution_evidence = {}
        if not self.gpu_execution_authorized:
            raise RestorationError(
                "ERR_GW_GPU_NOT_AUTHORIZED",
                "Candidate v3 GPU execution requires explicit authorization",
                retryable=False,
            )
        if request.workflow_id != self.workflow_id:
            raise RestorationError(
                "ERR_GW_WORKFLOW_INVALID",
                f"request workflowId {request.workflow_id!r} does not match Candidate v3 adapter workflow",
                retryable=False,
            )

        resolution = resolve_candidate_v3_params(case_id=request.case_id, requested=request.params)
        effective_params = resolution.params

        validate_candidate_v3_graph(self.workflow)
        crop_size, mask_size = self._validate_canonical_inputs(request)
        if hashlib.sha256(request.a2.image_bytes).hexdigest() != request.a2.sha256:
            raise RestorationError(
                "ERR_GW_A2_HASH_MISMATCH",
                "Candidate v3 identity reference hash does not match its bytes",
                retryable=False,
            )

        started = time.monotonic()
        try:
            crop_ref = self.client.upload_image(
                request.crop_png,
                "candidate_v3_canonical_image.png",
                run_id=request.run_id,
                attempt_id=request.attempt_id,
            )
            mask_ref = self.client.upload_image(
                request.mask.editable,
                "candidate_v3_canonical_editable_mask.png",
                run_id=request.run_id,
                attempt_id=request.attempt_id,
            )
            a2_ref = self.client.upload_image(
                request.a2.image_bytes,
                "candidate_v3_identity_reference.png",
                run_id=request.run_id,
                attempt_id=request.attempt_id,
            )
            bound = bind_candidate_v3_by_title(
                self.workflow,
                {
                    NODE_TITLES["LOAD_CROP"]: crop_ref.qualified_name,
                    NODE_TITLES["LOAD_MASK"]: mask_ref.qualified_name,
                    NODE_TITLES["LOAD_A2"]: a2_ref.qualified_name,
                },
                runtime_values={
                    "seed": request.seed,
                    "denoise": effective_params.denoise,
                    "steps": effective_params.steps,
                    "cfg": effective_params.cfg,
                    "sampler_name": effective_params.sampler,
                    "scheduler": effective_params.scheduler,
                },
            )
            prompt_id = self.client.submit_prompt(bound)
            image_info = self.client.poll_until_complete(
                prompt_id,
                timeout_seconds=min(self.timeout_seconds, effective_params.steps * 60 + 60),
            )
            png_bytes = self.client.download(image_info)
        except RestorationError:
            raise
        except (KeyError, TypeError, ValueError, OSError) as exc:
            raise RestorationError("ERR_GW_WORKFLOW_INVALID", str(exc), retryable=False) from exc

        try:
            restored = RestoredCrop.from_png_bytes(png_bytes)
        except Exception as exc:
            raise RestorationError("ERR_GW_EMPTY_OUTPUT", "Candidate v3 output is not a decodable PNG", False) from exc
        if (restored.width, restored.height) != CANONICAL_SIZE:
            raise RestorationError(
                "ERR_GW_GEOMETRY_MISMATCH",
                f"Candidate v3 output is {restored.width}x{restored.height}, expected 512x512",
                retryable=False,
            )
        self._last_execution_evidence = {
            "candidateProfileId": self.candidate_profile_id,
            "workflowId": self.workflow_id,
            "workflowSha256": self.workflow_sha256,
            "workflowHash": self.workflow_sha256,
            "boundConfig": {
                "seed": request.seed,
                "denoise": effective_params.denoise,
                "steps": effective_params.steps,
                "cfg": effective_params.cfg,
                "sampler": effective_params.sampler,
                "scheduler": effective_params.scheduler,
                "effectiveConfigSha256": _effective_config_sha256(request, effective_params, self.workflow_sha256),
                "caseId": request.case_id,
                "authoritySource": resolution.source,
                "authorityConfigId": resolution.config_id,
                "authorityConfigSha256": resolution.config_sha256,
                "canonicalSize": {"width": crop_size[0], "height": crop_size[1]},
            },
            "selectedReferenceHashes": [request.a2.sha256],
            "modelIdentifiers": list(self.model_identifiers),
            "gpuEvidence": dict(self.gpu_evidence or {"status": "NOT_CAPTURED"}),
            "promptId": prompt_id,
            "timingMs": int((time.monotonic() - started) * 1000),
            "inputGeometry": {"width": crop_size[0], "height": crop_size[1]},
            "outputGeometry": {"width": restored.width, "height": restored.height},
        }
        return restored

    def execution_evidence(self) -> dict[str, Any]:
        return dict(self._last_execution_evidence)

    def describe(self) -> RestorerDescriptor:
        return RestorerDescriptor(
            restorer_id=self.restorer_id,
            workflow_id=self.workflow_id,
            workflow_sha256=self.workflow_sha256,
            model_identifiers=self.model_identifiers,
        )

    @staticmethod
    def _validate_canonical_inputs(request: RestorationRequest) -> tuple[tuple[int, int], tuple[int, int]]:
        try:
            with Image.open(BytesIO(request.crop_png)) as crop:
                crop_size = crop.size
            with Image.open(BytesIO(request.mask.editable)) as mask:
                mask_size = mask.size
                mask_mode = mask.mode
            with Image.open(BytesIO(request.mask.feather)) as feather:
                feather_size = feather.size
                feather_mode = feather.mode
        except Exception as exc:
            raise RestorationError("ERR_GW_GEOMETRY_MISMATCH", "canonical image or mask is undecodable", False) from exc
        if (
            crop_size != CANONICAL_SIZE
            or mask_size != CANONICAL_SIZE
            or feather_size != CANONICAL_SIZE
            or mask_mode != "L"
            or feather_mode != "L"
        ):
            raise RestorationError(
                "ERR_GW_GEOMETRY_MISMATCH",
                "Candidate v3 requires 512x512 image, editable mask, and feather mask in L mode; "
                f"got image={crop_size}, editable={mask_size}/{mask_mode!r}, "
                f"feather={feather_size}/{feather_mode!r}",
                retryable=False,
            )
        return crop_size, mask_size


def _effective_config_sha256(
    request: RestorationRequest, params: Any, workflow_sha256: str
) -> str:
    payload = {
        "workflowId": request.workflow_id,
        "workflowSha256": workflow_sha256,
        "seed": request.seed,
        "caseId": request.case_id,
        "params": asdict(params),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()
