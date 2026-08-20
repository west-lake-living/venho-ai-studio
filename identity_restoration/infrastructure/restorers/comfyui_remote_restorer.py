from __future__ import annotations

from dataclasses import dataclass

from ...application.ports.identity_restorer import IdentityRestorerPort, RestorerDescriptor
from ...domain.entities import RestorationRequest, RestoredCrop
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

    def restore(self, request: RestorationRequest) -> RestoredCrop:
        crop_ref = self.client.upload_image(request.crop_png, "crop.png",
                                            run_id=request.run_id, attempt_id=request.attempt_id)
        mask_ref = self.client.upload_image(request.mask.editable, "mask.png",
                                            run_id=request.run_id, attempt_id=request.attempt_id)
        a2_ref = self.client.upload_image(request.a2.image_bytes, "a2.png",
                                          run_id=request.run_id, attempt_id=request.attempt_id)
        bound = bind_by_title(self.workflow, {
            NODE_TITLES["LOAD_CROP"]: crop_ref.qualified_name,
            NODE_TITLES["LOAD_MASK"]: mask_ref.qualified_name,
            NODE_TITLES["LOAD_A2"]: a2_ref.qualified_name,
        })
        prompt_id = self.client.submit_prompt(bound)
        image_info = self.client.poll_until_complete(prompt_id, timeout_seconds=self.timeout_seconds)
        png_bytes = self.client.download(image_info)
        return RestoredCrop.from_png_bytes(png_bytes)

    def describe(self) -> RestorerDescriptor:
        return RestorerDescriptor(restorer_id="comfyui-remote", workflow_id=self.workflow_id,
                                  workflow_sha256=self.workflow_sha256, model_identifiers=self.model_identifiers)
