"""AVIF intake contract for shared/vision/image_loader.

The vision API cannot read AVIF, so Mode A/B/C convert on the way in. The rules
that matter: never write into the user's photo folder, never lose an image, and
never label the bytes as a format they are not.
"""
from __future__ import annotations

import pytest
from PIL import Image, features

from shared.vision import image_loader
from shared.vision.image_loader import image_to_base64, load_images

pytestmark = pytest.mark.skipif(not features.check("avif"),
                                reason="Pillow build has no AVIF support")


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    target = tmp_path / "cache"
    monkeypatch.setattr(image_loader, "AVIF_CACHE_DIR", target)
    return target


def _write_avif(path, color):
    Image.new("RGB", (16, 16), color).save(path, format="AVIF")


def test_conversion_never_writes_into_the_source_folder(tmp_path, cache_dir):
    source = tmp_path / "photos"
    source.mkdir()
    _write_avif(source / "room.avif", (10, 120, 200))

    paths = load_images(source)

    assert list(source.iterdir()) == [source / "room.avif"]
    assert paths[0].parent == cache_dir
    assert paths[0].suffix == ".jpg"


def test_avif_and_jpg_sharing_a_stem_are_two_separate_images(tmp_path, cache_dir):
    source = tmp_path / "photos"
    source.mkdir()
    _write_avif(source / "room.avif", (10, 120, 200))
    Image.new("RGB", (16, 16), (200, 40, 30)).save(source / "room.jpg")

    paths = load_images(source)

    assert len(paths) == 2, "de-duplicating by stem would silently drop one photo"


def test_edited_source_is_not_served_from_a_stale_cache_entry(tmp_path, cache_dir):
    source = tmp_path / "photos"
    source.mkdir()
    avif = source / "room.avif"
    _write_avif(avif, (10, 120, 200))
    first = load_images(source)[0]

    _write_avif(avif, (240, 20, 20))
    second = load_images(source)[0]

    assert first != second
    assert Image.open(second).convert("RGB").getpixel((8, 8))[0] > 200


def test_repeat_run_reuses_the_cached_conversion(tmp_path, cache_dir):
    source = tmp_path / "photos"
    source.mkdir()
    _write_avif(source / "room.avif", (10, 120, 200))

    assert load_images(source) == load_images(source)
    assert len(list(cache_dir.iterdir())) == 1


def test_converted_image_is_sent_as_jpeg(tmp_path, cache_dir):
    source = tmp_path / "photos"
    source.mkdir()
    _write_avif(source / "room.avif", (10, 120, 200))

    _, media_type = image_to_base64(load_images(source)[0])

    assert media_type == "image/jpeg"


def test_avif_bytes_are_never_labelled_as_jpeg(tmp_path):
    avif = tmp_path / "room.avif"
    _write_avif(avif, (10, 120, 200))

    assert image_to_base64(avif)[1] == "image/avif"
