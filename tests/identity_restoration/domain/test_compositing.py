from __future__ import annotations

from identity_restoration.domain.compositing import composite_crop_into_canvas
from identity_restoration.domain.entities import RestoredCrop


def test_composite_only_changes_pixels_inside_crop_box(base_canvas_png, crop_transform, full_canvas_mask_png):
    from io import BytesIO

    from PIL import Image

    patch = Image.new("RGBA", (16, 16), (255, 0, 0, 255))
    buf = BytesIO()
    patch.save(buf, format="PNG")
    restored = RestoredCrop(png_bytes=buf.getvalue(), width=16, height=16)

    result = composite_crop_into_canvas(base_canvas_png=base_canvas_png, restored=restored,
                                        transform=crop_transform, editable_mask_png=full_canvas_mask_png)

    before = Image.open(BytesIO(base_canvas_png)).convert("RGBA")
    after = Image.open(BytesIO(result)).convert("RGBA")
    assert before.size == after.size
    # inside the box: changed
    assert after.getpixel((10, 10)) == (255, 0, 0, 255)
    # outside the box: untouched
    assert after.getpixel((0, 0)) == before.getpixel((0, 0))


def test_composite_rejects_size_mismatch(base_canvas_png, crop_transform, full_canvas_mask_png):
    import pytest

    bad = RestoredCrop(png_bytes=b"", width=1, height=1)
    from io import BytesIO

    from PIL import Image
    buf = BytesIO()
    Image.new("RGBA", (1, 1), (1, 2, 3, 255)).save(buf, format="PNG")
    bad = RestoredCrop(png_bytes=buf.getvalue(), width=1, height=1)

    with pytest.raises(ValueError):
        composite_crop_into_canvas(base_canvas_png=base_canvas_png, restored=bad,
                                   transform=crop_transform, editable_mask_png=full_canvas_mask_png)
