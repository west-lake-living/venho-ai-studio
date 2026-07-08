"""Phase 7 — Overlay merge tests.

Verifies merge rules per v2.4 §5.2:
  - apply_overlay(dna, None) → DNA unchanged
  - forbidden:             curated prepend, observed append, dedup
  - wording_overrides:     replace existing invariant value, mark value_source = "curated"
  - allowed_imperfections: curated first, observed second, dedup
  - notes → curator_notes: replaced fresh from overlay each run
  - Overlay does NOT touch evidence_count, coverage, consistency
"""

from __future__ import annotations

from pathlib import Path

import pytest

from knowledge_studio.vision.overlay_merge import apply_overlay, load_overlay
from knowledge_studio.vision.schemas.base import (
    AllowedImperfection,
    BaseDNA,
    EvidenceSummary,
    ForbiddenRule,
    InvariantFeature,
    VariableFeature,
)

BASE_DIR = Path(__file__).parent.parent


def _minimal_dna(**kwargs) -> BaseDNA:
    defaults = dict(
        subject="test",
        dna_version="1.0",
        schema_version="1.0",
        prompt_version="1.0",
        generated_at="2026-01-01T00:00:00",
        source_images=["h1", "h2"],
        invariant=[],
        variable=[],
        forbidden=[],
        evidence=EvidenceSummary(total_images=2),
    )
    defaults.update(kwargs)
    return BaseDNA(**defaults)


def _inv(key: str, value: str, **kwargs) -> InvariantFeature:
    return InvariantFeature(key=key, value=value, evidence_count=5, coverage=0.9, consistency=0.85, **kwargs)


# ---------------------------------------------------------------------------
# TestApplyOverlayEmpty
# ---------------------------------------------------------------------------

class TestApplyOverlayEmpty:
    def test_none_overlay_returns_same_dna(self):
        dna = _minimal_dna(invariant=[_inv("floor", "dark wood")])
        result = apply_overlay(dna, None)
        assert result.invariant[0].value == "dark wood"

    def test_empty_dict_overlay_returns_same_dna(self):
        dna = _minimal_dna(forbidden=[ForbiddenRule(rule="carpet", source="observed")])
        result = apply_overlay(dna, {})
        assert result.forbidden[0].rule == "carpet"


# ---------------------------------------------------------------------------
# TestForbiddenMerge
# ---------------------------------------------------------------------------

class TestForbiddenMerge:
    def test_curated_forbidden_prepends_observed(self):
        dna = _minimal_dna(
            forbidden=[ForbiddenRule(rule="carpet", source="observed")]
        )
        overlay = {"forbidden": ["no wallpaper"]}
        result = apply_overlay(dna, overlay)
        assert result.forbidden[0].rule == "no wallpaper"
        assert result.forbidden[0].source == "curated"
        assert result.forbidden[1].rule == "carpet"
        assert result.forbidden[1].source == "observed"

    def test_curated_deduplicates_observed_same_rule(self):
        dna = _minimal_dna(
            forbidden=[ForbiddenRule(rule="no carpet", source="observed")]
        )
        overlay = {"forbidden": ["no carpet"]}
        result = apply_overlay(dna, overlay)
        # Only 1 entry — observed deduped because curated covers it
        assert len(result.forbidden) == 1
        assert result.forbidden[0].source == "curated"

    def test_case_insensitive_dedup(self):
        dna = _minimal_dna(
            forbidden=[ForbiddenRule(rule="No Carpet", source="observed")]
        )
        overlay = {"forbidden": ["no carpet"]}
        result = apply_overlay(dna, overlay)
        assert len(result.forbidden) == 1

    def test_multiple_curated_forbidden_prepend_all(self):
        dna = _minimal_dna(
            forbidden=[ForbiddenRule(rule="carpet", source="observed")]
        )
        overlay = {"forbidden": ["no flowers", "no wallpaper"]}
        result = apply_overlay(dna, overlay)
        assert result.forbidden[0].source == "curated"
        assert result.forbidden[1].source == "curated"
        assert result.forbidden[2].source == "observed"


# ---------------------------------------------------------------------------
# TestWordingOverrides
# ---------------------------------------------------------------------------

class TestWordingOverrides:
    def test_wording_override_replaces_invariant_value(self):
        dna = _minimal_dna(invariant=[_inv("floor", "dark wood")])
        overlay = {"wording_overrides": {"floor": "dark hardwood floor"}}
        result = apply_overlay(dna, overlay)
        assert result.invariant[0].value == "dark hardwood floor"

    def test_wording_override_marks_value_source_curated(self):
        dna = _minimal_dna(invariant=[_inv("floor", "dark wood")])
        overlay = {"wording_overrides": {"floor": "dark hardwood floor"}}
        result = apply_overlay(dna, overlay)
        assert result.invariant[0].value_source == "curated"

    def test_wording_override_does_not_touch_coverage(self):
        dna = _minimal_dna(invariant=[_inv("floor", "dark wood")])
        overlay = {"wording_overrides": {"floor": "dark hardwood floor"}}
        result = apply_overlay(dna, overlay)
        assert result.invariant[0].coverage == pytest.approx(0.9)
        assert result.invariant[0].evidence_count == 5

    def test_wording_override_unknown_key_is_noop(self):
        dna = _minimal_dna(invariant=[_inv("floor", "dark wood")])
        overlay = {"wording_overrides": {"ceiling": "white painted"}}
        result = apply_overlay(dna, overlay)
        assert result.invariant[0].value == "dark wood"


# ---------------------------------------------------------------------------
# TestAllowedImperfections
# ---------------------------------------------------------------------------

class TestAllowedImperfectionsMerge:
    def test_curated_ai_prepends_observed_ai(self):
        dna = _minimal_dna(
            allowed_imperfections=[AllowedImperfection(value="slight scratches", source="observed")]
        )
        overlay = {"allowed_imperfections": ["minor dust on surfaces"]}
        result = apply_overlay(dna, overlay)
        assert result.allowed_imperfections[0].value == "minor dust on surfaces"
        assert result.allowed_imperfections[0].source == "curated"
        assert result.allowed_imperfections[1].value == "slight scratches"
        assert result.allowed_imperfections[1].source == "observed"

    def test_curated_ai_deduplicates_observed(self):
        dna = _minimal_dna(
            allowed_imperfections=[AllowedImperfection(value="minor dust", source="observed")]
        )
        overlay = {"allowed_imperfections": ["minor dust"]}
        result = apply_overlay(dna, overlay)
        assert len(result.allowed_imperfections) == 1
        assert result.allowed_imperfections[0].source == "curated"


# ---------------------------------------------------------------------------
# TestCuratorNotes
# ---------------------------------------------------------------------------

class TestCuratorNotes:
    def test_curator_notes_set_from_overlay_notes(self):
        dna = _minimal_dna()
        overlay = {"notes": ["This is a curated note", "Second note"]}
        result = apply_overlay(dna, overlay)
        assert result.curator_notes == ["This is a curated note", "Second note"]

    def test_curator_notes_idempotent_on_reapply(self):
        dna = _minimal_dna()
        overlay = {"notes": ["Note A"]}
        result = apply_overlay(dna, overlay)
        # Apply again — same overlay, same notes (idempotent)
        result2 = apply_overlay(result, overlay)
        assert result2.curator_notes == ["Note A"]

    def test_empty_overlay_notes_clears_curator_notes(self):
        dna = _minimal_dna(curator_notes=["old note"])
        overlay = {"notes": []}
        result = apply_overlay(dna, overlay)
        assert result.curator_notes == []


# ---------------------------------------------------------------------------
# TestLoadOverlay
# ---------------------------------------------------------------------------

class TestLoadOverlay:
    def test_load_overlay_returns_dict_for_existing_subject(self):
        overlay = load_overlay("venho_hotel", "lake_view_room")
        assert overlay is not None
        assert isinstance(overlay, dict)

    def test_load_overlay_returns_none_for_missing_subject(self):
        overlay = load_overlay("venho_hotel", "xyz_nonexistent_1234")
        assert overlay is None
