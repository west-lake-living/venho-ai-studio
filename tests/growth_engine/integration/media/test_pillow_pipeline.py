from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image, ImageOps

from growth_engine.adapters.outbound.media.pillow_processor import (
    MEDIA_INPUT_TOO_LARGE,
    MEDIA_PIXEL_LIMIT_EXCEEDED,
    MEDIA_UNSUPPORTED_FORMAT,
    MediaProcessingError,
    PillowImageProcessor,
)
from growth_engine.domain.media.media_policy import FACEBOOK_PHOTO_V1, INSTAGRAM_PHOTO_V1
from tests.growth_engine.support.image_fixtures import (
    make_alpha_png,
    make_heic,
    make_html_with_jpg_extension,
    make_orientation_jpeg,
    make_pixel_bomb_png,
    make_truncated_jpeg,
)


@pytest.mark.parametrize("orientation", range(1, 9))
def test_exif_orientation_is_applied_once_and_removed(
    tmp_path: Path,
    orientation: int,
) -> None:
    image_bytes = make_orientation_jpeg(orientation)
    source = _source_file(tmp_path, image_bytes)
    normalized = PillowImageProcessor().normalize(source, FACEBOOK_PHOTO_V1.spec)

    with Image.open(BytesIO(image_bytes)) as opened:
        expected = ImageOps.exif_transpose(opened).convert("RGB")
    with Image.open(BytesIO(normalized.data)) as result:
        assert result.format == "JPEG"
        assert result.getexif().get(274) is None
        expected_size = (80, 60) if orientation <= 4 else (60, 80)
        assert result.size == expected.size == expected_size
        samples = ((20, 15), (60, 15), (20, 45), (60, 45)) if orientation <= 4 else (
            (15, 20), (45, 20), (15, 60), (45, 60)
        )
        for point in samples:
            actual = result.getpixel(point)
            wanted = expected.getpixel(point)
            assert max(abs(a - b) for a, b in zip(actual, wanted)) < 35


def test_png_alpha_is_composited_on_profile_background(tmp_path: Path) -> None:
    normalized = PillowImageProcessor().normalize(
        _source_file(tmp_path, make_alpha_png()), FACEBOOK_PHOTO_V1.spec
    )
    with Image.open(BytesIO(normalized.data)) as result:
        background = result.getpixel((2, 2))
        blended = result.getpixel((20, 10))
    expected_background = (247, 244, 239)
    assert max(abs(a - b) for a, b in zip(background, expected_background)) <= 5
    assert blended[0] > 245 and 110 <= blended[1] <= 140 and 105 <= blended[2] <= 135


def test_instagram_profile_pads_to_four_by_five_without_crop(tmp_path: Path) -> None:
    normalized = PillowImageProcessor().normalize(
        _source_file(tmp_path, make_orientation_jpeg(1)), INSTAGRAM_PHOTO_V1.spec
    )
    assert normalized.width * 5 == normalized.height * 4
    with Image.open(BytesIO(normalized.data)) as result:
        assert result.getpixel((1, 1)) == pytest.approx((247, 244, 239), abs=8)
        assert result.getpixel((normalized.width // 2, normalized.height // 2))[0] > 180


@pytest.mark.parametrize(
    ("image_bytes", "expected_code"),
    [
        (make_html_with_jpg_extension(), MEDIA_UNSUPPORTED_FORMAT),
        (make_truncated_jpeg(), "MEDIA_DECODE_FAILED"),
        (make_pixel_bomb_png(), MEDIA_PIXEL_LIMIT_EXCEEDED),
    ],
)
def test_invalid_or_oversized_images_are_rejected_with_codes(
    tmp_path: Path,
    image_bytes: bytes,
    expected_code: str,
) -> None:
    with pytest.raises(MediaProcessingError) as caught:
        PillowImageProcessor().normalize(_source_file(tmp_path, image_bytes), FACEBOOK_PHOTO_V1.spec)
    assert caught.value.code == expected_code


def test_heic_decodes_when_encoder_is_available(tmp_path: Path) -> None:
    image_bytes = make_heic()
    if image_bytes is None:
        pytest.skip("pillow-heif HEIF encoder is unavailable")
    normalized = PillowImageProcessor().normalize(
        _source_file(tmp_path, image_bytes), FACEBOOK_PHOTO_V1.spec
    )
    assert normalized.mime == "image/jpeg"
    assert normalized.width == 64
    assert normalized.height == 48


def test_same_input_and_profile_produce_same_sha256(tmp_path: Path) -> None:
    image_bytes = make_orientation_jpeg(6)
    source = _source_file(tmp_path, image_bytes)
    first = PillowImageProcessor().normalize(source, INSTAGRAM_PHOTO_V1.spec)
    second = PillowImageProcessor().normalize(source, INSTAGRAM_PHOTO_V1.spec)
    assert first.sha256 == second.sha256
    assert first.data == second.data


def test_input_byte_limit_is_enforced_before_decode(tmp_path: Path) -> None:
    source = _source_file(tmp_path, b"\xff\xd8\xff" + b"0" * (25 * 1024 * 1024))
    with pytest.raises(MediaProcessingError) as caught:
        PillowImageProcessor().normalize(source, FACEBOOK_PHOTO_V1.spec)
    assert caught.value.code == MEDIA_INPUT_TOO_LARGE


def _source_file(tmp_path: Path, image_bytes: bytes) -> Path:
    path = tmp_path / "generated-input.jpg"
    path.write_bytes(image_bytes)
    return path
