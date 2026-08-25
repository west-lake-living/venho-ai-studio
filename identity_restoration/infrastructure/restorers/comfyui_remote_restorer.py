from __future__ import annotations

from dataclasses import dataclass, field
from dataclasses import asdict
from io import BytesIO

from PIL import Image

from ...application.ports.identity_restorer import IdentityRestorerPort, RestorerDescriptor
from ...domain.entities import RestorationRequest, RestoredCrop
from ...domain.errors import RestorationError
from ..comfyui.graph_binder import bind_by_title
from ..comfyui.http_client import ComfyUIHttpClient
from ..comfyui.node_registry import NODE_TITLES

# GW-P3: the Windows GPU worker adapter. Same Port as ComfyUILocalRestorer —
# that equivalence is the entire point of ADR-GW-001. Needs a live worker
# reachable at ``client.base_url``; this class has NO offline test coverage
# for the network path itself (0-network invariant, v2.0 PHẦN 12.1) — it is
# exercised through recorded HTTP fixtures once GW-P3-T9 records a real run.


@dataclass
class ComfyUIRemoteRestorer:
    client: ComfyUIHttpClient
    workflow: dict
    workflow_id: str
    workflow_sha256: str
    model_identifiers: tuple[str, ...] = ()
    timeout_seconds: float = 600.0
    restorer_id: str = "comfyui-remote"
    _last_execution_evidence: dict[str, Any] = field(default_factory=dict, init=False, repr=False)

    def restore(self, request: RestorationRequest) -> RestoredCrop:
        self._last_execution_evidence = {}
        crop_ref = self.client.upload_image(request.crop_png, "crop.png",
                                            run_id=request.run_id, attempt_id=request.attempt_id)
        mask_ref = self.client.upload_image(request.mask.editable, "mask.png",
                                            run_id=request.run_id, attempt_id=request.attempt_id)
        a2_ref = self.client.upload_image(request.a2.image_bytes, "a2.png",
                                          run_id=request.run_id, attempt_id=request.attempt_id)
        crop_size = Image.open(BytesIO(request.crop_png)).size
        mask_size = Image.open(BytesIO(request.mask.editable)).size
        if crop_size != mask_size:
            raise RestorationError(
                "ERR_GW_GEOMETRY_MISMATCH",
                f"remote crop/mask dimensions differ: {crop_size} != {mask_size}",
                retryable=False,
            )
        geometry_values = None
        if self.workflow_id == "face_restore_win_sd15_ipadapter_v2":
            width, height = crop_size
            geometry_values = {
                "padRight": (8 - (width % 8)) % 8,
                "padBottom": (8 - (height % 8)) % 8,
                "finalCropWidth": width,
                "finalCropHeight": height,
            }
        try:
            bound = bind_by_title(self.workflow, {
                NODE_TITLES["LOAD_CROP"]: crop_ref.qualified_name,
                NODE_TITLES["LOAD_MASK"]: mask_ref.qualified_name,
                NODE_TITLES["LOAD_A2"]: a2_ref.qualified_name,
            }, runtime_values={"seed": request.seed, **asdict(request.params)},
               geometry_values=geometry_values)
        except RestorationError:
            raise
        except (TypeError, ValueError) as exc:
            raise RestorationError("ERR_GW_WORKFLOW_INVALID", str(exc), retryable=False) from exc
        prompt_id = self.client.submit_prompt(bound)
        image_info = self.client.poll_until_complete(prompt_id, timeout_seconds=self.timeout_seconds)
        png_bytes = self.client.download(image_info)
        self._last_execution_evidence = {
            "promptId": prompt_id,
            "remoteHost": self.client.base_url,
            "remoteOutput": {
                "filename": image_info.get("filename"),
                "subfolder": image_info.get("subfolder", ""),
                "type": image_info.get("type", "output"),
            },
        }
        restored = RestoredCrop.from_png_bytes(png_bytes)
        restored.assert_geometry_matches(request)
        if geometry_values is not None:
            self._last_execution_evidence["geometry"] = {
                **geometry_values,
                "inputWidth": crop_size[0],
                "inputHeight": crop_size[1],
                "paddedWidth": crop_size[0] + geometry_values["padRight"],
                "paddedHeight": crop_size[1] + geometry_values["padBottom"],
            }
        return restored

    def execution_evidence(self) -> dict[str, Any]:
        """Return metadata from the last real backend call, never fabricate it."""
        return dict(self._last_execution_evidence)

    def free_memory(self) -> dict[str, Any]:
        """Use the already-approved ComfyUI resident-model release endpoint."""
        return dict(self.client.free_memory())

    def describe(self) -> RestorerDescriptor:
        return RestorerDescriptor(restorer_id="comfyui-remote", workflow_id=self.workflow_id,
                                  workflow_sha256=self.workflow_sha256, model_identifiers=self.model_identifiers)
