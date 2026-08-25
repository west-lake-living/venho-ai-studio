from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from identity_restoration.domain.entities import CropTransform, MaskSet
from identity_restoration.domain.value_objects import RestorationParams


def _png_bytes(size: tuple[int, int], color: tuple[int, int, int, int]) -> bytes:
    image = Image.new("RGBA", size, color)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def base_canvas_png() -> bytes:
    return _png_bytes((64, 64), (10, 20, 30, 255))


@pytest.fixture
def crop_png() -> bytes:
    return _png_bytes((16, 16), (100, 110, 120, 255))


@pytest.fixture
def crop_transform() -> CropTransform:
    return CropTransform(source_x=8, source_y=8, source_w=16, source_h=16, target_size=16)


@pytest.fixture
def full_canvas_mask_png() -> bytes:
    """L-mode mask, sized to the canvas, white (editable) only inside the crop box."""
    mask = Image.new("L", (64, 64), 0)
    inner = Image.new("L", (16, 16), 255)
    mask.paste(inner, (8, 8))
    buffer = BytesIO()
    mask.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def mask_set(full_canvas_mask_png: bytes) -> MaskSet:
    return MaskSet(editable=full_canvas_mask_png, feather=full_canvas_mask_png, version="test_v1")


@pytest.fixture
def restoration_params() -> RestorationParams:
    return RestorationParams(denoise=0.45, steps=28, cfg=5.5, sampler="dpmpp_2m", scheduler="karras")


@pytest.fixture
def a2_png() -> bytes:
    return _png_bytes((32, 32), (200, 150, 90, 255))


@pytest.fixture
def restore_command_factory(crop_png, mask_set, base_canvas_png, crop_transform, restoration_params):
    from identity_restoration.application.dto.restore_command import RestoreCommand

    def _build(*, restorer_id: str = "mock", a2_sha256: str, seed: int = 42,
               restoration_mask=mask_set, full_canvas_mask=mask_set):
        return RestoreCommand(
            run_id="run-test", attempt_id="attempt-1", restorer_id=restorer_id,
            crop_png=crop_png, mask=restoration_mask, full_canvas_mask=full_canvas_mask,
            base_canvas_png=base_canvas_png,
            crop_transform=crop_transform, a2_path="fake/a2.png", a2_sha256=a2_sha256,
            workflow_id="mock-workflow", seed=seed, params=restoration_params,
        )

    return _build
