"""Phase 6 — Cache key includes schema_id + new canonical subjects."""

from pathlib import Path
from datetime import datetime

import pytest

from knowledge_studio.vision.pass1_observe import _cache_path, observe_all
from knowledge_studio.vision.subject_resolver import resolve
from shared.vision.client import MockVisionClient

BASE_DIR = Path(__file__).parent.parent
ASSETS_DIR = BASE_DIR / "assets" / "raw"


# ---------------------------------------------------------------------------
# Cache key includes schema_id (§cache fix Phase 6)
# ---------------------------------------------------------------------------

class TestCacheKeyIncludesSchemaId:
    def test_cache_key_differs_for_different_schema_ids(self):
        obs_dir = Path("/tmp/obs")
        img_hash = "a" * 64
        p1 = _cache_path(obs_dir, img_hash, "venho_hotel.room_2", "1.0", "1.0")
        p2 = _cache_path(obs_dir, img_hash, "venho_hotel.lake_view_room", "1.0", "1.0")
        assert p1 != p2, "Same image + different schema_id must produce different cache paths"

    def test_cache_key_same_for_same_schema_id(self):
        obs_dir = Path("/tmp/obs")
        img_hash = "b" * 64
        p1 = _cache_path(obs_dir, img_hash, "venho_hotel.deluxe_double", "1.0", "1.0")
        p2 = _cache_path(obs_dir, img_hash, "venho_hotel.deluxe_double", "1.0", "1.0")
        assert p1 == p2

    def test_cache_key_includes_schema_id_in_filename(self):
        obs_dir = Path("/tmp/obs")
        img_hash = "c" * 64
        p = _cache_path(obs_dir, img_hash, "venho_hotel.lake_view_room", "1.0", "1.0")
        assert "venho_hotel.lake_view_room" in p.name

    def test_cache_key_changes_with_schema_version(self):
        obs_dir = Path("/tmp/obs")
        img_hash = "d" * 64
        schema_id = "venho_hotel.room"
        p1 = _cache_path(obs_dir, img_hash, schema_id, "1.0", "1.0")
        p2 = _cache_path(obs_dir, img_hash, schema_id, "2.0", "1.0")
        assert p1 != p2

    def test_cache_key_changes_with_prompt_version(self):
        obs_dir = Path("/tmp/obs")
        img_hash = "e" * 64
        schema_id = "venho_hotel.room"
        p1 = _cache_path(obs_dir, img_hash, schema_id, "1.0", "1.0")
        p2 = _cache_path(obs_dir, img_hash, schema_id, "1.0", "2.0")
        assert p1 != p2


# ---------------------------------------------------------------------------
# New canonical subjects resolve correctly (Phase 5 coverage, Phase 6 confirm)
# ---------------------------------------------------------------------------

class TestNewSubjectsResolvable:
    def test_lake_view_room_resolves(self):
        sd = resolve("venho_hotel", "lake_view_room")
        assert sd.name == "lake_view_room"
        assert sd.schema_id == "venho_hotel.lake_view_room"
        assert sd.overlay_path is not None

    def test_deluxe_double_resolves(self):
        sd = resolve("venho_hotel", "deluxe_double")
        assert sd.name == "deluxe_double"
        assert sd.schema_id == "venho_hotel.deluxe_double"
        assert sd.overlay_path is not None

    def test_lake_view_room_schema_id_in_cache_path(self):
        sd = resolve("venho_hotel", "lake_view_room")
        obs_dir = Path("/tmp/obs")
        p = _cache_path(obs_dir, "a" * 64, sd.schema_id, "1.0", "1.0")
        assert "lake_view_room" in p.name

    def test_deluxe_double_schema_id_in_cache_path(self):
        sd = resolve("venho_hotel", "deluxe_double")
        obs_dir = Path("/tmp/obs")
        p = _cache_path(obs_dir, "b" * 64, sd.schema_id, "1.0", "1.0")
        assert "deluxe_double" in p.name


# ---------------------------------------------------------------------------
# No cross-schema cache contamination with mock
# ---------------------------------------------------------------------------

class TestNoCrossSchemaContamination:
    def test_different_subjects_get_different_cache_files(self, tmp_path):
        """Running two subjects on the same image should write to different cache paths."""
        sd_lake = resolve("venho_hotel", "lake_view_room")
        sd_deluxe = resolve("venho_hotel", "deluxe_double")

        fake_image = tmp_path / "test.jpg"
        from PIL import Image as PILImage
        img = PILImage.new("RGB", (100, 100), color=(100, 150, 200))
        img.save(fake_image)

        client = MockVisionClient()
        obs_dir = tmp_path / "obs"

        observe_all([fake_image], obs_dir, client, "1.0", "1.0", sd_lake, concurrency=1)
        observe_all([fake_image], obs_dir, client, "1.0", "1.0", sd_deluxe, concurrency=1)

        # Both subjects should have written their own cache file
        cache_files = list(obs_dir.glob("*.json"))
        assert len(cache_files) == 2, (
            f"Expected 2 separate cache files (one per schema_id), got {len(cache_files)}: "
            f"{[f.name for f in cache_files]}"
        )
        names = [f.name for f in cache_files]
        assert any("lake_view_room" in n for n in names)
        assert any("deluxe_double" in n for n in names)

    def test_same_subject_second_run_is_cache_hit(self, tmp_path):
        """Second run with same subject on same image → cache hit (0 API calls)."""
        sd = resolve("venho_hotel", "lake_view_room")

        fake_image = tmp_path / "test.jpg"
        from PIL import Image as PILImage
        img = PILImage.new("RGB", (100, 100), color=(50, 100, 150))
        img.save(fake_image)

        client = MockVisionClient()
        obs_dir = tmp_path / "obs"

        _, r1 = observe_all([fake_image], obs_dir, client, "1.0", "1.0", sd, concurrency=1)
        _, r2 = observe_all([fake_image], obs_dir, client, "1.0", "1.0", sd, concurrency=1)

        assert r1.cache_hits == 0
        assert r2.cache_hits == 1


# ---------------------------------------------------------------------------
# Raw asset folders exist (sanity check before Mode B runs)
# ---------------------------------------------------------------------------

class TestRawAssetsExist:
    def test_lake_view_room_images_exist(self):
        folder = ASSETS_DIR / "room" / "ViewHo-room-2"
        assert folder.is_dir(), f"Missing: {folder}"
        images = list(folder.glob("*.jpg")) + list(folder.glob("*.jpeg")) + list(folder.glob("*.JPG"))
        assert len(images) >= 6, f"Expected ≥6 images, found {len(images)}"

    def test_deluxe_double_images_exist(self):
        folder = ASSETS_DIR / "room" / "VenHo-room-1"
        assert folder.is_dir(), f"Missing: {folder}"
        images = list(folder.glob("*.jpg")) + list(folder.glob("*.jpeg")) + list(folder.glob("*.JPG"))
        assert len(images) >= 3, f"Expected ≥3 images, found {len(images)}"
