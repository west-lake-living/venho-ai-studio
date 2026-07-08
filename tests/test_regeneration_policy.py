"""Phase 7 — DNA regeneration policy tests.

Verifies:
  - hashes_changed() logic
  - needs_regeneration() logic (hashes + schema/prompt version drift)
  - bump_version() format
  - archive_dna() moves files to _archive/
  - load_manifest() / save_manifest() round-trip
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from knowledge_studio.vision.dna_manifest import (
    hashes_changed,
    needs_regeneration,
    bump_version,
    archive_dna,
    load_manifest,
    save_manifest,
)
from knowledge_studio.vision.schemas.base import BaseDNA, EvidenceSummary

BASE_DIR = Path(__file__).parent.parent


def _minimal_dna(**kwargs) -> BaseDNA:
    defaults = dict(
        subject="test",
        dna_version="1.0",
        schema_version="1.0",
        prompt_version="1.0",
        generated_at="2026-01-01T00:00:00",
        source_images=["hash_a", "hash_b"],
        invariant=[],
        variable=[],
        forbidden=[],
        evidence=EvidenceSummary(total_images=2),
    )
    defaults.update(kwargs)
    return BaseDNA(**defaults)


# ---------------------------------------------------------------------------
# TestHashesChanged
# ---------------------------------------------------------------------------

class TestHashesChanged:
    def test_none_manifest_always_changed(self):
        assert hashes_changed(None, ["hash_a"]) is True

    def test_same_hashes_not_changed(self):
        manifest = {"source_hashes": ["hash_a", "hash_b"]}
        assert hashes_changed(manifest, ["hash_a", "hash_b"]) is False

    def test_different_hashes_changed(self):
        manifest = {"source_hashes": ["hash_a"]}
        assert hashes_changed(manifest, ["hash_b"]) is True

    def test_order_does_not_matter(self):
        manifest = {"source_hashes": ["hash_b", "hash_a"]}
        assert hashes_changed(manifest, ["hash_a", "hash_b"]) is False

    def test_added_image_is_changed(self):
        manifest = {"source_hashes": ["hash_a"]}
        assert hashes_changed(manifest, ["hash_a", "hash_b"]) is True

    def test_removed_image_is_changed(self):
        manifest = {"source_hashes": ["hash_a", "hash_b"]}
        assert hashes_changed(manifest, ["hash_a"]) is True


# ---------------------------------------------------------------------------
# TestNeedsRegeneration
# ---------------------------------------------------------------------------

class TestNeedsRegeneration:
    def _stable_manifest(self):
        return {
            "source_hashes": ["hash_x", "hash_y"],
            "schema_version": "1.0",
            "prompt_version": "1.0",
        }

    def test_none_manifest_requires_regeneration(self):
        assert needs_regeneration(None, ["hash_x"], "1.0", "1.0") is True

    def test_no_change_no_regeneration(self):
        manifest = self._stable_manifest()
        assert needs_regeneration(manifest, ["hash_x", "hash_y"], "1.0", "1.0") is False

    def test_hash_change_requires_regeneration(self):
        manifest = self._stable_manifest()
        assert needs_regeneration(manifest, ["hash_z"], "1.0", "1.0") is True

    def test_schema_version_drift_requires_regeneration(self):
        manifest = self._stable_manifest()
        assert needs_regeneration(manifest, ["hash_x", "hash_y"], "1.1", "1.0") is True

    def test_prompt_version_drift_requires_regeneration(self):
        manifest = self._stable_manifest()
        assert needs_regeneration(manifest, ["hash_x", "hash_y"], "1.0", "1.1") is True

    def test_both_versions_changed_requires_regeneration(self):
        manifest = self._stable_manifest()
        assert needs_regeneration(manifest, ["hash_x", "hash_y"], "1.1", "1.1") is True


# ---------------------------------------------------------------------------
# TestBumpVersion
# ---------------------------------------------------------------------------

class TestBumpVersion:
    def test_1_0_becomes_1_1(self):
        assert bump_version("1.0") == "1.1"

    def test_1_9_becomes_1_10(self):
        assert bump_version("1.9") == "1.10"

    def test_2_0_becomes_2_1(self):
        assert bump_version("2.0") == "2.1"

    def test_invalid_version_gets_dot_1_appended(self):
        result = bump_version("invalid")
        assert result.endswith(".1")


# ---------------------------------------------------------------------------
# TestArchiveDNA
# ---------------------------------------------------------------------------

class TestArchiveDNA:
    def test_archive_moves_md_to_archive(self, tmp_path):
        kd = tmp_path / "knowledge"
        kd.mkdir()
        (kd / "VENHO_HOTEL_ROOM_DNA.md").write_text("# old dna", encoding="utf-8")
        archive_dna(kd, "VENHO_HOTEL_ROOM_DNA", "1.0")
        assert not (kd / "VENHO_HOTEL_ROOM_DNA.md").exists()
        archive_files = list((kd / "_archive").glob("*.md"))
        assert len(archive_files) == 1
        assert "v1.0" in archive_files[0].name

    def test_archive_moves_json_to_archive(self, tmp_path):
        kd = tmp_path / "knowledge"
        kd.mkdir()
        (kd / "VENHO_HOTEL_ROOM_DNA.json").write_text("{}", encoding="utf-8")
        archive_dna(kd, "VENHO_HOTEL_ROOM_DNA", "1.0")
        assert not (kd / "VENHO_HOTEL_ROOM_DNA.json").exists()
        archive_files = list((kd / "_archive").glob("*.json"))
        assert len(archive_files) == 1

    def test_archive_creates_archive_dir(self, tmp_path):
        kd = tmp_path / "knowledge"
        kd.mkdir()
        (kd / "VENHO_HOTEL_ROOM_DNA.md").write_text("# content", encoding="utf-8")
        assert not (kd / "_archive").exists()
        archive_dna(kd, "VENHO_HOTEL_ROOM_DNA", "1.0")
        assert (kd / "_archive").is_dir()

    def test_archive_noop_when_no_files(self, tmp_path):
        kd = tmp_path / "knowledge"
        kd.mkdir()
        archive_dna(kd, "VENHO_HOTEL_ROOM_DNA", "1.0")
        assert not (kd / "_archive").exists() or not list((kd / "_archive").glob("*"))


# ---------------------------------------------------------------------------
# TestManifestRoundTrip
# ---------------------------------------------------------------------------

class TestManifestRoundTrip:
    def test_save_and_load_manifest(self, tmp_path):
        kd = tmp_path / "knowledge"
        kd.mkdir()
        dna = _minimal_dna(subject="room")
        save_manifest(kd, "room", dna, overlay_applied=True)
        manifest = load_manifest(kd, "room")
        assert manifest is not None
        assert manifest["subject"] == "room"
        assert manifest["current_version"] == "1.0"
        assert manifest["overlay_applied"] is True

    def test_load_manifest_returns_none_when_missing(self, tmp_path):
        kd = tmp_path / "knowledge"
        kd.mkdir()
        assert load_manifest(kd, "nonexistent") is None

    def test_manifest_contains_schema_and_prompt_version(self, tmp_path):
        kd = tmp_path / "knowledge"
        kd.mkdir()
        dna = _minimal_dna(schema_version="1.2", prompt_version="1.1")
        save_manifest(kd, "lobby", dna)
        manifest = load_manifest(kd, "lobby")
        assert manifest["schema_version"] == "1.2"
        assert manifest["prompt_version"] == "1.1"
