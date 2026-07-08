"""Phase 7 — Mode B DNA JSON + Markdown contract tests.

Verifies:
  - BaseDNA contract_version = "1.1"
  - All required fields present in JSON dump
  - JSON round-trip via model_validate
  - render_dna_md produces all fixed sections
  - write_dna_output produces .md and .json (+ optional COMPACT)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from knowledge_studio.vision.schemas.base import (
    BaseDNA,
    EvidenceSummary,
    InvariantFeature,
    VariableFeature,
    ForbiddenRule,
    AllowedImperfection,
    WeakFeature,
)

BASE_DIR = Path(__file__).parent.parent

MODE_B_REQUIRED_FIELDS = (
    "contract_version", "mode", "project", "subject", "dna_version",
    "schema_id", "schema_version", "prompt_version", "provider", "model",
    "generated_at", "source_images", "invariant", "variable",
    "allowed_imperfections", "forbidden", "evidence",
    "future_capture_notes", "curator_notes",
)

MODE_B_MD_SECTIONS = (
    "# PROJECT SUBJECT DNA",
    "## META",
    "## INVARIANT",
    "## VARIABLE",
    "## ALLOWED IMPERFECTIONS",
    "## FORBIDDEN",
    "## EVIDENCE",
    "## WEAK FEATURES",
    "## FUTURE CAPTURE NOTES",
    "## CURATOR NOTES",
)


def _minimal_dna(**kwargs) -> BaseDNA:
    defaults = dict(
        subject="test_subject",
        dna_version="1.0",
        schema_version="1.0",
        prompt_version="1.0",
        generated_at="2026-01-01T00:00:00",
        source_images=["hash_abc123", "hash_def456"],
        invariant=[],
        variable=[],
        forbidden=[],
        evidence=EvidenceSummary(total_images=2),
    )
    defaults.update(kwargs)
    return BaseDNA(**defaults)


# ---------------------------------------------------------------------------
# TestModeBContract — JSON schema
# ---------------------------------------------------------------------------

class TestModeBContract:
    def test_contract_version_is_1_1(self):
        dna = _minimal_dna()
        assert dna.contract_version == "1.1"

    def test_all_required_fields_in_json_dump(self):
        dna = _minimal_dna()
        data = dna.model_dump()
        for field in MODE_B_REQUIRED_FIELDS:
            assert field in data, f"Missing required field: {field}"

    def test_mode_is_b(self):
        dna = _minimal_dna()
        assert dna.mode == "B"

    def test_json_round_trip(self):
        dna = _minimal_dna(project="venho_hotel", provider="openai")
        dumped = dna.model_dump_json()
        restored = BaseDNA.model_validate_json(dumped)
        assert restored.subject == dna.subject
        assert restored.contract_version == "1.1"
        assert restored.project == "venho_hotel"

    def test_invariant_features_serialized(self):
        feat = InvariantFeature(key="floor", value="dark wood", evidence_count=5, coverage=0.9, consistency=0.85)
        dna = _minimal_dna(invariant=[feat])
        data = dna.model_dump()
        assert len(data["invariant"]) == 1
        assert data["invariant"][0]["key"] == "floor"
        assert data["invariant"][0]["coverage"] == pytest.approx(0.9)

    def test_forbidden_rules_serialized(self):
        rule = ForbiddenRule(rule="no carpet", source="curated")
        dna = _minimal_dna(forbidden=[rule])
        data = dna.model_dump()
        assert data["forbidden"][0]["rule"] == "no carpet"
        assert data["forbidden"][0]["source"] == "curated"

    def test_allowed_imperfections_serialized(self):
        ai = AllowedImperfection(value="minor scratches", source="curated")
        dna = _minimal_dna(allowed_imperfections=[ai])
        data = dna.model_dump()
        assert data["allowed_imperfections"][0]["value"] == "minor scratches"

    def test_evidence_total_images(self):
        dna = _minimal_dna(evidence=EvidenceSummary(total_images=10))
        assert dna.evidence.total_images == 10

    def test_weak_features_in_evidence(self):
        ev = EvidenceSummary(total_images=3, weak_features=[WeakFeature(key="curtain", evidence_count=1)])
        dna = _minimal_dna(evidence=ev)
        assert len(dna.evidence.weak_features) == 1

    def test_string_coercion_for_forbidden(self):
        dna = _minimal_dna(forbidden=["carpet flooring"])
        assert dna.forbidden[0].rule == "carpet flooring"
        assert dna.forbidden[0].source == "observed"


# ---------------------------------------------------------------------------
# TestModeBMarkdown — render_dna_md
# ---------------------------------------------------------------------------

class TestModeBMarkdown:
    def test_render_has_all_fixed_sections(self):
        from knowledge_studio.vision.renderers.dna_md import render_dna_md
        dna = _minimal_dna()
        md = render_dna_md(dna)
        for section in MODE_B_MD_SECTIONS:
            assert section in md, f"Missing section: {section}"

    def test_render_meta_contains_subject(self):
        from knowledge_studio.vision.renderers.dna_md import render_dna_md
        dna = _minimal_dna(subject="lake_view_room")
        md = render_dna_md(dna)
        assert "lake_view_room" in md

    def test_render_meta_contains_contract_version(self):
        from knowledge_studio.vision.renderers.dna_md import render_dna_md
        dna = _minimal_dna()
        md = render_dna_md(dna)
        assert "1.1" in md

    def test_render_invariant_shows_evidence(self):
        from knowledge_studio.vision.renderers.dna_md import render_dna_md
        feat = InvariantFeature(key="floor", value="dark wood", evidence_count=8, coverage=0.95, consistency=0.9)
        dna = _minimal_dna(invariant=[feat])
        md = render_dna_md(dna)
        assert "dark wood" in md
        assert "evidence: 8" in md

    def test_render_curated_invariant_tagged(self):
        from knowledge_studio.vision.renderers.dna_md import render_dna_md
        feat = InvariantFeature(
            key="floor", value="dark hardwood floor", value_source="curated",
            evidence_count=8, coverage=0.95, consistency=0.9
        )
        dna = _minimal_dna(invariant=[feat])
        md = render_dna_md(dna)
        assert "[curated]" in md

    def test_render_forbidden_tagged_with_source(self):
        from knowledge_studio.vision.renderers.dna_md import render_dna_md
        dna = _minimal_dna(forbidden=[ForbiddenRule(rule="no carpet", source="curated")])
        md = render_dna_md(dna)
        assert "no carpet" in md
        assert "[curated]" in md

    def test_render_project_in_meta(self):
        from knowledge_studio.vision.renderers.dna_md import render_dna_md
        dna = _minimal_dna()
        md = render_dna_md(dna, project="venho_hotel")
        assert "venho_hotel" in md


# ---------------------------------------------------------------------------
# TestModeBOutput — write_dna_output
# ---------------------------------------------------------------------------

class TestModeBOutput:
    def test_write_produces_md_and_json(self, tmp_path):
        from knowledge_studio.vision.renderers.dna_md import write_dna_output
        dna = _minimal_dna()
        paths = write_dna_output(dna, tmp_path, "VENHO_TEST_DNA")
        assert paths["md"].exists()
        assert paths["json"].exists()

    def test_json_file_has_contract_version_1_1(self, tmp_path):
        from knowledge_studio.vision.renderers.dna_md import write_dna_output
        dna = _minimal_dna()
        paths = write_dna_output(dna, tmp_path, "VENHO_TEST_DNA")
        data = json.loads(paths["json"].read_text(encoding="utf-8"))
        assert data["contract_version"] == "1.1"

    def test_md_file_has_project_subject_dna_header(self, tmp_path):
        from knowledge_studio.vision.renderers.dna_md import write_dna_output
        dna = _minimal_dna()
        paths = write_dna_output(dna, tmp_path, "VENHO_TEST_DNA")
        md = paths["md"].read_text(encoding="utf-8")
        assert "# PROJECT SUBJECT DNA" in md

    def test_compact_file_written_when_requested(self, tmp_path):
        from knowledge_studio.vision.renderers.dna_md import write_dna_output
        dna = _minimal_dna()
        paths = write_dna_output(dna, tmp_path, "VENHO_TEST_DNA", write_compact=True)
        assert "compact" in paths
        assert paths["compact"].exists()
        assert "_COMPACT.md" in paths["compact"].name

    def test_compact_not_written_by_default(self, tmp_path):
        from knowledge_studio.vision.renderers.dna_md import write_dna_output
        dna = _minimal_dna()
        paths = write_dna_output(dna, tmp_path, "VENHO_TEST_DNA")
        assert "compact" not in paths

    def test_json_round_trip_from_file(self, tmp_path):
        from knowledge_studio.vision.renderers.dna_md import write_dna_output
        feat = InvariantFeature(key="floor", value="marble", evidence_count=4, coverage=0.8, consistency=0.9)
        dna = _minimal_dna(subject="lobby", invariant=[feat])
        paths = write_dna_output(dna, tmp_path, "VENHO_LOBBY_DNA")
        data = json.loads(paths["json"].read_text(encoding="utf-8"))
        restored = BaseDNA.model_validate(data)
        assert restored.subject == "lobby"
        assert restored.invariant[0].key == "floor"
