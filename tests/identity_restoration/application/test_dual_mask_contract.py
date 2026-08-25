from __future__ import annotations

from io import BytesIO

from PIL import Image

from identity_restoration.domain.compositing import composite_crop_into_canvas
from identity_restoration.domain.entities import MaskSet, RestoredCrop
from identity_restoration.infrastructure.restorers.mock_restorer import MockIdentityRestorer


class CapturingRestorer(MockIdentityRestorer):
    request = None

    def restore(self, request):
        type(self).request = request
        return super().restore(request)


def _png_size(data: bytes) -> tuple[int, int]:
    with Image.open(BytesIO(data)) as image:
        return image.size


def test_remote_port_receives_crop_mask_but_pixel_lock_uses_full_canvas_mask(
    build_use_case, restore_command_factory, full_canvas_mask_png
):
    crop_mask = Image.new("L", (16, 16), 255)
    crop_buffer = BytesIO()
    crop_mask.save(crop_buffer, format="PNG")
    crop_local = crop_buffer.getvalue()
    crop_set = MaskSet(editable=crop_local, feather=crop_local, version="crop-local-v1")
    full_set = MaskSet(
        editable=full_canvas_mask_png,
        feather=full_canvas_mask_png,
        version="full-canvas-v1",
    )

    restorer = CapturingRestorer()
    use_case = build_use_case(a2_sha256="deadbeef", restorer=restorer)
    result = use_case.execute(
        restore_command_factory(
            a2_sha256="deadbeef",
            restoration_mask=crop_set,
            full_canvas_mask=full_set,
        )
    )

    assert result.status == "NEEDS_REVIEW"
    assert CapturingRestorer.request is not None
    assert CapturingRestorer.request.mask.editable == crop_local
    assert _png_size(CapturingRestorer.request.mask.editable) == (16, 16)
    assert _png_size(full_set.editable) == (64, 64)
    assert result.composite_path is not None
    assert result.pixel_lock is not None and result.pixel_lock.passed
    assert result.lineage["maskSpaces"]["restoration"]["coordinateSpace"] == "crop-local"
    assert result.lineage["maskSpaces"]["preservation"]["coordinateSpace"] == "full-canvas"


def test_composite_and_pixel_lock_preserve_full_canvas_dimensions(
    build_use_case, restore_command_factory, full_canvas_mask_png, base_canvas_png, crop_transform
):
    use_case = build_use_case(a2_sha256="deadbeef")
    result = use_case.execute(
        restore_command_factory(
            a2_sha256="deadbeef",
            full_canvas_mask=MaskSet(
                editable=full_canvas_mask_png,
                feather=full_canvas_mask_png,
                version="full-canvas-v1",
            ),
        )
    )

    assert result.status == "NEEDS_REVIEW"
    assert result.pixel_lock is not None and result.pixel_lock.passed
    assert _png_size(base_canvas_png) == (64, 64)
    restored = Image.new("RGBA", (16, 16), (200, 150, 100, 255))
    buffer = BytesIO()
    restored.save(buffer, format="PNG")
    composite = composite_crop_into_canvas(
        base_canvas_png=base_canvas_png,
        restored=RestoredCrop.from_png_bytes(buffer.getvalue()),
        transform=crop_transform,
        editable_mask_png=full_canvas_mask_png,
    )
    assert _png_size(composite) == (64, 64)
