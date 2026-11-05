from __future__ import annotations

from io import BytesIO
from typing import Callable

from PIL import Image

from growth_engine.adapters.outbound.legacy.output_image_gate import (
    MAX_IMAGE_BYTES,
    check_output_image,
)


_SYNTHETIC = {"_synthetic": True}


def _jpeg(width: int = 800, height: int = 1000, orientation: int | None = None) -> bytes:
    image = Image.new("RGB", (width, height), color=(20, 40, 60))
    output = BytesIO()
    save_options = {}
    if orientation is not None:
        exif = Image.Exif()
        exif[274] = orientation
        save_options["exif"] = exif
    image.save(output, format="JPEG", **save_options)
    return output.getvalue()


def _check(data: bytes, fetch: Callable[[str], bytes] | None = None) -> list[str]:
    return check_output_image("https://synthetic.invalid/photo", fetch or (lambda _url: data))


def test_rejects_jpeg_that_requires_exif_rotation() -> None:
    assert "OUTPUT_IMAGE_EXIF_ORIENTATION" in _check(_jpeg(orientation=6))


def test_rejects_html_even_if_it_would_have_a_success_status() -> None:
    assert _check(b"<html><body>synthetic 200</body></html>") == ["OUTPUT_IMAGE_NOT_JPEG"]


def test_rejects_image_larger_than_five_mib() -> None:
    oversized = b"\xff\xd8\xff" + (b"x" * (MAX_IMAGE_BYTES + 1))
    assert _check(oversized) == ["OUTPUT_IMAGE_TOO_LARGE"]


def test_accepts_decodable_jpeg_inside_aspect_window() -> None:
    assert _check(_jpeg()) == []


def test_fetch_failure_is_a_blocking_issue() -> None:
    def fail(_url: str) -> bytes:
        raise OSError("synthetic fetch failure")

    assert _check(b"", fail) == ["OUTPUT_IMAGE_FETCH_FAILED"]


def test_rejects_corrupt_jpeg_and_out_of_window_aspect_ratio() -> None:
    assert _check(b"\xff\xd8\xffbroken") == ["OUTPUT_IMAGE_DECODE_FAILED"]
    assert "OUTPUT_IMAGE_ASPECT_RATIO" in _check(_jpeg(1200, 400))


def test_accepts_absent_or_normal_exif_orientation() -> None:
    assert _check(_jpeg(orientation=1)) == []
    assert _check(_jpeg(orientation=None)) == []
