"""Phase 7 — Subject resolver tests.

Verifies:
  - _dna_filename format
  - _observe_prompt_path: subject-specific vs universal fallback
  - _resolve_schema_path priority (project-specific > shared > universal)
  - resolve() returns correct SubjectDef for known Ven Hồ subjects
"""

from __future__ import annotations

from pathlib import Path

import pytest

from knowledge_studio.vision.subject_resolver import (
    _dna_filename,
    _observe_prompt_path,
    _resolve_schema_path,
    resolve,
)

BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"


# ---------------------------------------------------------------------------
# TestDnaFilename
# ---------------------------------------------------------------------------

class TestDnaFilename:
    def test_venho_hotel_room(self):
        assert _dna_filename("venho_hotel", "room") == "VENHO_HOTEL_ROOM_DNA"

    def test_venho_hotel_lake_view_room(self):
        assert _dna_filename("venho_hotel", "lake_view_room") == "VENHO_HOTEL_LAKE_VIEW_ROOM_DNA"

    def test_uppercase_project_and_subject(self):
        result = _dna_filename("my_project", "my_subject")
        assert result == "MY_PROJECT_MY_SUBJECT_DNA"

    def test_single_word_subject(self):
        assert _dna_filename("venho_hotel", "lobby") == "VENHO_HOTEL_LOBBY_DNA"


# ---------------------------------------------------------------------------
# TestObservePromptPath
# ---------------------------------------------------------------------------

class TestObservePromptPath:
    def test_linh_an_gets_specific_prompt(self):
        path = _observe_prompt_path("linh_an")
        assert path.exists(), f"linh_an-specific prompt not found: {path}"
        assert "linh_an" in path.name

    def test_unknown_subject_falls_back_to_universal(self):
        path = _observe_prompt_path("xyz_unknown_subject_1234")
        assert path.exists(), f"Universal prompt not found: {path}"
        assert "universal" in path.name

    def test_universal_subject_gets_universal_prompt(self):
        path = _observe_prompt_path("universal")
        assert "universal" in path.name


# ---------------------------------------------------------------------------
# TestResolveSchemaPath
# ---------------------------------------------------------------------------

class TestResolveSchemaPath:
    def test_venho_hotel_lake_view_room_resolves_project_specific(self):
        path, source = _resolve_schema_path("venho_hotel", "lake_view_room")
        assert path.exists()
        assert "venho_hotel" in source
        assert "lake_view_room" in source

    def test_venho_hotel_lobby_resolves_project_specific(self):
        path, source = _resolve_schema_path("venho_hotel", "lobby")
        assert path.exists()
        assert "lobby" in source

    def test_unknown_subject_falls_back_to_universal(self):
        path, source = _resolve_schema_path("venho_hotel", "xyz_unknown_1234")
        assert path.exists()
        assert "universal" in source

    def test_strict_resolve_rejects_universal_fallback(self):
        with pytest.raises(FileNotFoundError):
            _resolve_schema_path("linh_an", "nike_pink_running", allow_universal=False)

    def test_linh_an_sport_schema_resolves_project_specific(self):
        path, source = _resolve_schema_path("linh_an", "outfit_e_sport", allow_universal=False)
        assert path.exists()
        assert source == "config/projects/linh_an/subjects/outfit_e_sport.yaml"

    def test_source_description_contains_yaml_filename(self):
        _, source = _resolve_schema_path("venho_hotel", "lake_view_room")
        assert "lake_view_room.yaml" in source


# ---------------------------------------------------------------------------
# TestResolve
# ---------------------------------------------------------------------------

class TestResolve:
    def test_resolve_lake_view_room(self):
        subj = resolve("venho_hotel", "lake_view_room")
        assert subj.name == "lake_view_room"
        assert subj.dna_filename == "VENHO_HOTEL_LAKE_VIEW_ROOM_DNA"

    def test_resolve_lobby(self):
        subj = resolve("venho_hotel", "lobby")
        assert subj.name == "lobby"
        assert "LOBBY" in subj.dna_filename

    def test_resolve_returns_correct_dna_filename_format(self):
        subj = resolve("venho_hotel", "lake_view_room")
        assert subj.dna_filename.startswith("VENHO_HOTEL_")
        assert subj.dna_filename.endswith("_DNA")

    def test_resolve_includes_observe_prompt(self):
        subj = resolve("venho_hotel", "lake_view_room")
        assert subj.observe_prompt.exists()

    def test_resolve_schema_source_not_empty(self):
        subj = resolve("venho_hotel", "lake_view_room")
        assert subj.schema_source

    def test_resolve_overlay_path_for_subject_with_overlay(self):
        subj = resolve("venho_hotel", "lake_view_room")
        # lake_view_room has an overlay file
        assert subj.overlay_path is not None
        assert subj.overlay_path.exists()

    def test_resolve_aggregation_keys_not_empty(self):
        subj = resolve("venho_hotel", "lake_view_room")
        assert len(subj.aggregation_keys) > 0

    def test_resolve_observation_cls_is_base_observation_subclass(self):
        from knowledge_studio.vision.schemas.base import BaseObservation
        subj = resolve("venho_hotel", "lake_view_room")
        assert issubclass(subj.observation_cls, BaseObservation)

    def test_resolve_dna_cls_is_base_dna_subclass(self):
        from knowledge_studio.vision.schemas.base import BaseDNA
        subj = resolve("venho_hotel", "lake_view_room")
        assert issubclass(subj.dna_cls, BaseDNA)

    def test_room_schema_class_does_not_hardcode_venho_schema_id(self):
        from knowledge_studio.vision.schemas.room import RoomObservation, RoomDNA
        assert RoomObservation.model_fields["schema_id"].default == "universal"
        assert RoomDNA.model_fields["schema_id"].default == "universal"
