"""FORBIDDEN must hold prohibitions, never feature names.

Regression cover for the `outside` DNA, which listed "lake view", "railing" and
"Rooftop terrace" as forbidden — the subject's own defining features.
"""

from knowledge_studio.vision.forbidden_policy import is_prohibition, sanitize_forbidden
from knowledge_studio.vision.overlay_merge import apply_overlay
from knowledge_studio.vision.schemas.base import BaseDNA, EvidenceSummary, ForbiddenRule
from validator_studio.observe_adapter import _forbidden_rules_for_validation


def test_prohibitions_are_recognised():
    assert is_prohibition("no infinity pool or resort-style pool deck")
    assert is_prohibition("No visible outdoor furniture")
    assert is_prohibition("never show a rooftop bar")
    assert is_prohibition("without any marble interior")


def test_feature_names_are_not_prohibitions():
    for junk in ["lake view", "Lake view", "railing", "Rooftop terrace", "Cityscape", "lake_view", "Furniture"]:
        assert not is_prohibition(junk), junk


def test_sanitize_drops_junk_and_dedups_case_insensitively():
    assert sanitize_forbidden([
        "no marble interior",
        "lake view",
        "No Marble Interior",
        "Rooftop terrace",
        "no rooftop bar",
    ]) == ["no marble interior", "no rooftop bar"]


def _dna_with_forbidden(rules: list[ForbiddenRule]) -> BaseDNA:
    return BaseDNA(
        project="venho_hotel",
        subject="outside",
        dna_version="1.1",
        schema_id="venho_hotel.outside",
        schema_version="1.0",
        prompt_version="1.0",
        provider="test",
        model="test",
        generated_at="2026-08-07T00:00:00",
        source_images=[],
        invariant=[],
        variable=[],
        evidence=EvidenceSummary(total_images=0, weak_features=[]),
        forbidden=rules,
    )


def test_overlay_merge_drops_legacy_observed_junk():
    """DNA written before the sanitizer existed must not leak junk through the merge."""
    dna = _dna_with_forbidden([
        ForbiddenRule(rule="lake view", source="observed"),
        ForbiddenRule(rule="no city high-rise skyline in background", source="observed"),
    ])
    merged = apply_overlay(dna, {"forbidden": ["no infinity pool"]})
    rules = [f.rule for f in merged.forbidden]
    assert "lake view" not in rules
    assert rules == ["no infinity pool", "no city high-rise skyline in background"]


def test_validator_uses_curated_rules_only_when_present():
    """A violated rule is severity=high → kill-switch → a paid-for regenerate. Only human
    policy is allowed to trigger that."""
    dna = {"forbidden": [
        {"rule": "no infinity pool", "source": "curated"},
        {"rule": "No visible lake or cityscape", "source": "observed"},
    ]}
    assert [item["rule"] for item in _forbidden_rules_for_validation(dna)] == ["no infinity pool"]


def test_validator_falls_back_to_observed_without_curated_rules():
    dna = {"forbidden": [{"rule": "No visible railing", "source": "observed"}]}
    assert len(_forbidden_rules_for_validation(dna)) == 1
