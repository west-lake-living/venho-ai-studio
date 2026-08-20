from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from identity_restoration.domain.entities import A2Authority, RestorationRequest
from identity_restoration.domain.errors import RestorationError
from identity_restoration.domain.value_objects import RestorationParams
from identity_restoration.infrastructure.restorers.comfyui_local_restorer import ComfyUILocalRestorer


def _to_png(image: Image.Image) -> bytes:
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _request(crop_png, mask_set, a2):
    params = RestorationParams(denoise=0.45, steps=28, cfg=5.5, sampler="dpmpp_2m", scheduler="karras")
    return RestorationRequest(run_id="r", attempt_id="a", crop_png=crop_png, mask=mask_set, a2=a2,
                              workflow_id="face_restore_v1_api", seed=1, params=params)


def test_comfyui_local_restorer_wraps_existing_provider_without_touching_it(
    monkeypatch, crop_png, mask_set, a2_png
) -> None:
    """T3 (patch v2.1 §4): the wrapper must call the existing
    ComfyUIIdentityRestorer.restore() unchanged, in "no crop_box" mode
    (crop passed as base_image, no compositing inside the adapter) — proven
    here by asserting the exact kwargs the inner class receives."""
    captured: dict = {}

    def fake_restore(self, *, base_image, identity_reference, face_mask, geometry, config):
        captured["base_image_size"] = base_image.size
        captured["config_has_crop"] = "crop" in config
        captured["config_has_crop_box"] = "crop_box" in config
        captured["workflow"] = config["workflow"]
        restored = Image.new("RGBA", base_image.size, (1, 2, 3, 255))
        return restored

    monkeypatch.setattr(
        "image_studio_runtime.action_composite.providers.ComfyUIIdentityRestorer.restore",
        fake_restore,
    )

    adapter = ComfyUILocalRestorer(workflow={"1": {"_meta": {"title": "x"}}},
                                   workflow_id="face_restore_v1_api", workflow_sha256="deadbeef")
    a2 = A2Authority.from_bytes(a2_png)
    restored = adapter.restore(_request(crop_png, mask_set, a2))

    assert captured["config_has_crop"] is False
    assert captured["config_has_crop_box"] is False
    assert captured["base_image_size"] == (16, 16)
    assert restored.width == 16 and restored.height == 16
    assert restored.png_bytes != crop_png


def test_comfyui_local_restorer_maps_timeout_to_structured_error(monkeypatch, crop_png, mask_set, a2_png) -> None:
    def raise_timeout(self, **kwargs):
        raise TimeoutError("no response")

    monkeypatch.setattr(
        "image_studio_runtime.action_composite.providers.ComfyUIIdentityRestorer.restore", raise_timeout,
    )
    adapter = ComfyUILocalRestorer(workflow={}, workflow_id="face_restore_v1_api", workflow_sha256="deadbeef")
    a2 = A2Authority.from_bytes(a2_png)

    with pytest.raises(RestorationError) as exc_info:
        adapter.restore(_request(crop_png, mask_set, a2))

    assert exc_info.value.code == "ERR_GW_WORKER_TIMEOUT"
    assert exc_info.value.retryable is True


def test_comfyui_local_restorer_describe_carries_workflow_pin() -> None:
    adapter = ComfyUILocalRestorer(workflow={}, workflow_id="face_restore_v1_api", workflow_sha256="deadbeef",
                                   model_identifiers=("sdxl", "pulid"))
    descriptor = adapter.describe()
    assert descriptor.restorer_id == "comfyui-local"
    assert descriptor.workflow_id == "face_restore_v1_api"
    assert descriptor.workflow_sha256 == "deadbeef"
    assert descriptor.model_identifiers == ("sdxl", "pulid")
