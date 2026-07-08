"""Phase 7 — Mode A JSON + Markdown contract tests.

Verifies:
  - BaseObservation contract_version = "1.0"
  - All required fields present in JSON dump
  - JSON round-trip via model_validate
  - render_single_md produces all fixed sections
  - write_mode_a_output produces .md and .json files
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from knowledge_studio.vision.schemas.base import BaseObservation, ObservedFeature
from knowledge_studio.vision.schemas.universal import UniversalObservation

BASE_DIR = Path(__file__).parent.parent

MODE_A_REQUIRED_FIELDS = (
    "contract_version", "mode", "image_hash", "image_file",
    "subject", "schema_id", "schema_version", "prompt_version",
    "provider", "model", "observed_at", "features",
)

MODE_A_MD_SECTIONS = (
    "# IMAGE OBSERVATION",
    "## META",
    "## SUBJECT",
    "## SCENE",
    "## COMPOSITION",
    "## LIGHTING",
    "## PALETTE",
    "## MATERIALS",
    "## AI-USABLE NOTES",
    "## UNCERTAINTY",
)


def _minimal_obs(**kwargs) -> BaseObservation:
    defaults = dict(
        image_hash="abc123def456abc123",
        image_file="test.jpg",
        subject="universal",
        schema_version="1.0",
        prompt_version="1.0",
        observed_at="2026-01-01T00:00:00",
        features=[],
    )
    defaults.update(kwargs)
    return BaseObservation(**defaults)


# ---------------------------------------------------------------------------
# TestModeAContract — JSON schema
# ---------------------------------------------------------------------------

class TestModeAContract:
    def test_contract_version_is_1_0(self):
        obs = _minimal_obs()
        assert obs.contract_version == "1.0"

    def test_all_required_fields_in_json_dump(self):
        obs = _minimal_obs()
        data = obs.model_dump()
        for field in MODE_A_REQUIRED_FIELDS:
            assert field in data, f"Missing required field: {field}"

    def test_mode_defaults_to_b(self):
        obs = _minimal_obs()
        assert obs.mode == "B"

    def test_mode_a_flag_sets_mode(self):
        obs = _minimal_obs(mode="A")
        assert obs.mode == "A"

    def test_json_round_trip(self):
        obs = _minimal_obs(provider="mock", model="mock")
        dumped = obs.model_dump_json()
        restored = BaseObservation.model_validate_json(dumped)
        assert restored.image_hash == obs.image_hash
        assert restored.contract_version == obs.contract_version

    def test_features_list_in_dump(self):
        feat = ObservedFeature(
            key="floor", type="enum", value="hardwood", category="materials", confidence=0.95
        )
        obs = _minimal_obs(features=[feat])
        data = obs.model_dump()
        assert len(data["features"]) == 1
        assert data["features"][0]["key"] == "floor"

    def test_universal_observation_inherits_contract(self):
        obs = UniversalObservation(
            image_hash="aabbccdd",
            image_file="img.jpg",
            subject="universal",
            schema_version="1.0",
            prompt_version="1.0",
            observed_at="2026-01-01T00:00:00",
            features=[],
        )
        assert obs.contract_version == "1.0"
        assert obs.schema_id == "universal"


# ---------------------------------------------------------------------------
# TestModeAMarkdown — render_single_md
# ---------------------------------------------------------------------------

class TestModeAMarkdown:
    def test_render_has_all_fixed_sections(self):
        from knowledge_studio.vision.renderers.single_md import render_single_md
        obs = _minimal_obs(mode="A")
        md = render_single_md(obs)
        for section in MODE_A_MD_SECTIONS:
            assert section in md, f"Missing section: {section}"

    def test_render_meta_contains_image_file(self):
        from knowledge_studio.vision.renderers.single_md import render_single_md
        obs = _minimal_obs(image_file="hotel_room.jpg", mode="A")
        md = render_single_md(obs)
        assert "hotel_room.jpg" in md

    def test_render_meta_contains_schema_id(self):
        from knowledge_studio.vision.renderers.single_md import render_single_md
        obs = _minimal_obs(mode="A")
        md = render_single_md(obs)
        assert "universal" in md

    def test_render_meta_contains_contract_version(self):
        from knowledge_studio.vision.renderers.single_md import render_single_md
        obs = _minimal_obs(mode="A")
        md = render_single_md(obs)
        assert "1.0" in md

    def test_render_excludes_not_visible_features(self):
        from knowledge_studio.vision.renderers.single_md import render_single_md
        feat = ObservedFeature(
            key="window", type="enum", value="not_visible",
            category="scene", confidence=0.0,
        )
        obs = _minimal_obs(features=[feat], mode="A")
        md = render_single_md(obs)
        assert "not_visible" not in md

    def test_render_includes_visible_features(self):
        from knowledge_studio.vision.renderers.single_md import render_single_md
        feat = ObservedFeature(
            key="floor", type="enum", value="dark hardwood",
            category="materials", confidence=0.9,
        )
        obs = _minimal_obs(features=[feat], mode="A")
        md = render_single_md(obs)
        assert "dark hardwood" in md


# ---------------------------------------------------------------------------
# TestModeAOutput — write_mode_a_output
# ---------------------------------------------------------------------------

class TestModeAOutput:
    def test_write_produces_md_and_json(self, tmp_path):
        from knowledge_studio.vision.renderers.single_md import write_mode_a_output
        obs = _minimal_obs(image_file="room.jpg", mode="A")
        paths = write_mode_a_output(obs, tmp_path)
        assert paths["md"].exists()
        assert paths["json"].exists()

    def test_json_file_has_contract_version(self, tmp_path):
        from knowledge_studio.vision.renderers.single_md import write_mode_a_output
        obs = _minimal_obs(image_file="room.jpg", mode="A")
        paths = write_mode_a_output(obs, tmp_path)
        data = json.loads(paths["json"].read_text(encoding="utf-8"))
        assert data["contract_version"] == "1.0"

    def test_md_file_has_image_observation_header(self, tmp_path):
        from knowledge_studio.vision.renderers.single_md import write_mode_a_output
        obs = _minimal_obs(image_file="room.jpg", mode="A")
        paths = write_mode_a_output(obs, tmp_path)
        md = paths["md"].read_text(encoding="utf-8")
        assert "# IMAGE OBSERVATION" in md

    def test_filename_includes_hash_prefix(self, tmp_path):
        from knowledge_studio.vision.renderers.single_md import write_mode_a_output
        obs = _minimal_obs(image_file="lobby.jpg", image_hash="abcdef1234567890")
        paths = write_mode_a_output(obs, tmp_path)
        assert "abcdef12" in paths["md"].name

    def test_json_round_trip_from_file(self, tmp_path):
        from knowledge_studio.vision.renderers.single_md import write_mode_a_output
        obs = _minimal_obs(image_file="room.jpg", provider="mock", mode="A")
        paths = write_mode_a_output(obs, tmp_path)
        data = json.loads(paths["json"].read_text(encoding="utf-8"))
        restored = BaseObservation.model_validate(data)
        assert restored.image_hash == obs.image_hash
        assert restored.provider == "mock"
