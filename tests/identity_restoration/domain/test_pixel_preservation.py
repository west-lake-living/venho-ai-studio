from __future__ import annotations

from io import BytesIO

from PIL import Image

from identity_restoration.domain.policies.pixel_preservation import assert_pixels_preserved


def _png(size, color):
    buf = BytesIO()
    Image.new("RGBA", size, color).save(buf, format="PNG")
    return buf.getvalue()


def test_pixel_lock_passes_when_only_editable_region_changes() -> None:
    before = Image.new("RGBA", (20, 20), (10, 10, 10, 255))
    after = before.copy()
    for x in range(5, 10):
        for y in range(5, 10):
            after.putpixel((x, y), (200, 0, 0, 255))
    mask = Image.new("L", (20, 20), 0)
    for x in range(5, 10):
        for y in range(5, 10):
            mask.putpixel((x, y), 255)

    def to_bytes(img):
        b = BytesIO()
        img.save(b, format="PNG")
        return b.getvalue()

    report = assert_pixels_preserved(before_canvas=to_bytes(before), after_canvas=to_bytes(after),
                                     editable_mask=to_bytes(mask))
    assert report.passed
    assert report.mutated_pixel_count == 0


def test_pixel_lock_fails_hard_even_when_change_is_outside_mask_by_one_pixel() -> None:
    before = Image.new("RGBA", (10, 10), (10, 10, 10, 255))
    after = before.copy()
    after.putpixel((0, 0), (255, 255, 255, 255))  # outside the mask entirely
    mask = Image.new("L", (10, 10), 0)  # nothing editable

    def to_bytes(img):
        b = BytesIO()
        img.save(b, format="PNG")
        return b.getvalue()

    report = assert_pixels_preserved(before_canvas=to_bytes(before), after_canvas=to_bytes(after),
                                     editable_mask=to_bytes(mask))
    assert not report.passed
    assert report.mutated_pixel_count >= 1
