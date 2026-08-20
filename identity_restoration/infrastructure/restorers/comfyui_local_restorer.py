from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from typing import Any

from PIL import Image

from image_studio_runtime.action_composite.providers import ComfyUIIdentityRestorer

from ...application.ports.identity_restorer import IdentityRestorerPort, RestorerDescriptor
from ...domain.entities import RestorationRequest, RestoredCrop
from ...domain.errors import RestorationError

# GW-P2-T3 (patch v2.1 §2.3 / §4): this wraps the EXISTING, already-running
# ComfyUIIdentityRestorer (image_studio_runtime/action_composite/providers.py)
# unchanged. It does not re-implement HTTP, upload, polling or download.
#
# Behaviour contract kept identical to the pre-refactor call path: the crop
# passed to this adapter is submitted to ComfyUI as the whole "base_image"
# (no crop/crop_box in config), so the inner restorer takes its own
# no-crop branch and returns the raw restored image at input size — the same
# bytes it would have returned before this Port existed. Compositing that
# result back into the canvas is the new domain layer's job
# (identity_restoration/domain/compositing.py), not this adapter's.
#
# Golden-master parity: since the inner class and its HTTP behaviour are
# untouched, a live ComfyUI server that reproduces tests/identity_restoration/
# golden/ outputs through the OLD call path will reproduce the same bytes
# through this adapter too. That equivalence is a live-server check
# (`venho-restore run --restorer comfyui-local`) outside this workspace's
# reach in an offline/pytest context; it is not asserted by any offline test.


@dataclass
class ComfyUILocalRestorer:
    workflow: dict[str, Any]
    workflow_id: str
    workflow_sha256: str
    endpoint: str = "http://127.0.0.1:8188"
    timeout_seconds: float = 120.0
    node_bindings: dict[str, str] | None = None
    model_identifiers: tuple[str, ...] = ()
    restorer_id: str = "comfyui-local"
    _inner: ComfyUIIdentityRestorer = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._inner = ComfyUIIdentityRestorer(endpoint=self.endpoint, request_timeout=self.timeout_seconds)

    def restore(self, request: RestorationRequest) -> RestoredCrop:
        crop_image = Image.open(BytesIO(request.crop_png)).convert("RGBA")
        mask_image = Image.open(BytesIO(request.mask.editable)).convert("L")
        config: dict[str, Any] = {
            "workflow": self.workflow,
            "timeout_seconds": self.timeout_seconds,
            "node_bindings": self.node_bindings or {},
        }
        try:
            restored_image = self._inner.restore(
                base_image=crop_image,
                identity_reference=request.a2.image_bytes,
                face_mask=mask_image,
                geometry={},
                config=config,
            )
        except TimeoutError as exc:
            raise RestorationError("ERR_GW_WORKER_TIMEOUT", str(exc), retryable=True) from exc
        except RuntimeError as exc:
            raise RestorationError("ERR_GW_WORKFLOW_INVALID", str(exc), retryable=False) from exc
        except OSError as exc:
            raise RestorationError("ERR_GW_WORKER_OFFLINE", str(exc), retryable=True) from exc

        buffer = BytesIO()
        restored_image.save(buffer, format="PNG")
        return RestoredCrop(png_bytes=buffer.getvalue(), width=restored_image.width, height=restored_image.height)

    def describe(self) -> RestorerDescriptor:
        return RestorerDescriptor(
            restorer_id="comfyui-local",
            workflow_id=self.workflow_id,
            workflow_sha256=self.workflow_sha256,
            model_identifiers=self.model_identifiers,
        )

    def health_check(self) -> bool:
        return self._inner.health_check()
