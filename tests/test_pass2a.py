"""Tests for Pass 2A deterministic consolidation per §4 of Master Plan v2.3."""

import pytest
from datetime import datetime
from knowledge_studio.vision.pass2_consolidate import _pass2a
from knowledge_studio.vision.schemas.base import BaseObservation, ObservedFeature


AGGREGATION_KEYS = [
    {"key": "window_frame", "type": "enum", "values": ["black_aluminum", "white_pvc", "not_visible"]},
    {"key": "lighting_condition", "type": "enum", "values": ["natural_daylight", "artificial_warm", "mixed"]},
    {"key": "wall_color", "type": "free"},
    {"key": "wall_artwork", "type": "enum", "values": ["three_floral_prints", "none", "not_visible"]},
    {"key": "rare_feature", "type": "free"},
]

THRESHOLDS = {
    "consolidation_threshold": 0.6,
    "consistency_threshold": 0.7,
    "weak_threshold": 0.3,
}


def make_obs(idx: int, features: list[dict]) -> BaseObservation:
    return BaseObservation(
        image_hash=f"hash{idx:04d}" * 4,
        image_file=f"img_{idx}.jpg",
        subject="room",
        schema_version="1.0",
        prompt_version="1.0",
        observed_at=datetime.now().isoformat(),
        features=[ObservedFeature(**f) for f in features],
    )


class TestInvariantClassification:
    """Test §4: coverage >= threshold AND consistency >= threshold → INVARIANT."""

    def test_stable_feature_becomes_invariant(self):
        """window_frame = black_aluminum in all 4 images → INVARIANT."""
        observations = [
            make_obs(i, [
                {"key": "window_frame", "type": "enum", "value": "black_aluminum", "category": "structure", "confidence": 0.95},
            ])
            for i in range(4)
        ]
        result = _pass2a(observations, AGGREGATION_KEYS, [], THRESHOLDS)
        assert "window_frame" in result["invariant_raw"]
        inv = result["invariant_raw"]["window_frame"]
        assert inv["coverage"] == 1.0
        assert inv["consistency"] == 1.0


class TestVariableClassification:
    """Test §4: coverage >= threshold BUT consistency < threshold → VARIABLE."""

    def test_lighting_high_coverage_but_changing_value_is_variable(self):
        """KEY INVARIANT FROM v2.3: lighting appears in ALL images but value changes → VARIABLE."""
        lighting_values = ["natural_daylight", "artificial_warm", "natural_daylight", "mixed"]
        observations = [
            make_obs(i, [
                {"key": "lighting_condition", "type": "enum", "value": v, "category": "lighting", "confidence": 0.90},
            ])
            for i, v in enumerate(lighting_values)
        ]
        result = _pass2a(observations, AGGREGATION_KEYS, [], THRESHOLDS)
        assert "lighting_condition" in result["variable_raw"], (
            "lighting_condition appears in all 4 images but value changes → must be VARIABLE, not INVARIANT"
        )
        assert "lighting_condition" not in result["invariant_raw"]

    def test_value_range_contains_all_unique_values(self):
        lighting_values = ["natural_daylight", "artificial_warm", "natural_daylight", "mixed"]
        observations = [
            make_obs(i, [
                {"key": "lighting_condition", "type": "enum", "value": v, "category": "lighting", "confidence": 0.90},
            ])
            for i, v in enumerate(lighting_values)
        ]
        result = _pass2a(observations, AGGREGATION_KEYS, [], THRESHOLDS)
        value_range = set(result["variable_raw"]["lighting_condition"]["value_set"])
        assert "natural_daylight" in value_range
        assert "artificial_warm" in value_range
        assert "mixed" in value_range


class TestWeakFeatureClassification:
    """Test §4: coverage < weak_threshold → WEAK FEATURE."""

    def test_rare_feature_in_one_of_four_images_is_weak(self):
        """rare_feature appears in 1/4 images = 25% < weak_threshold 30% → WEAK."""
        observations = [
            make_obs(0, [
                {"key": "rare_feature", "type": "free", "value": "some decoration", "category": "furniture", "confidence": 0.7},
            ]),
            make_obs(1, []),
            make_obs(2, []),
            make_obs(3, []),
        ]
        result = _pass2a(observations, AGGREGATION_KEYS, [], THRESHOLDS)
        assert "rare_feature" in result["weak_raw"]
        assert result["weak_raw"]["rare_feature"]["evidence_count"] == 1


class TestDeterminism:
    """Test: running Pass 2A twice on same data produces identical results."""

    def test_identical_results_on_two_runs(self):
        observations = [
            make_obs(i, [
                {"key": "window_frame", "type": "enum", "value": "black_aluminum", "category": "structure", "confidence": 0.95},
                {"key": "lighting_condition", "type": "enum", "value": ["natural_daylight", "artificial_warm"][i % 2], "category": "lighting", "confidence": 0.9},
            ])
            for i in range(4)
        ]
        result1 = _pass2a(observations, AGGREGATION_KEYS, [], THRESHOLDS)
        result2 = _pass2a(observations, AGGREGATION_KEYS, [], THRESHOLDS)

        assert result1["invariant_raw"] == result2["invariant_raw"]
        assert result1["variable_raw"] == result2["variable_raw"]
        assert result1["weak_raw"] == result2["weak_raw"]


class TestForbiddenMerge:
    """Test: FORBIDDEN = union of forbidden_hints + defaults."""

    def test_forbidden_merges_defaults_and_hints(self):
        observations = [
            make_obs(0, [], forbidden_hints=["no floor-to-ceiling glass"]),
            make_obs(1, [], forbidden_hints=["no marble interior"]),
            make_obs(2, []),
        ]
        result = _pass2a(observations, AGGREGATION_KEYS, ["no luxury resort"], THRESHOLDS)
        assert "no luxury resort" in result["forbidden"]
        assert "no floor-to-ceiling glass" in result["forbidden"]
        assert "no marble interior" in result["forbidden"]
        assert len(set(result["forbidden"])) == len(result["forbidden"]), "No duplicates in forbidden"


def make_obs_with_hints(idx: int, features: list[dict], forbidden_hints: list[str] = None) -> BaseObservation:
    return BaseObservation(
        image_hash=f"hash{idx:04d}" * 4,
        image_file=f"img_{idx}.jpg",
        subject="room",
        schema_version="1.0",
        prompt_version="1.0",
        observed_at=datetime.now().isoformat(),
        features=[ObservedFeature(**f) for f in features],
        forbidden_hints=forbidden_hints or [],
    )


# Patch make_obs to support forbidden_hints
def make_obs(idx: int, features: list[dict], forbidden_hints: list[str] = None) -> BaseObservation:
    return BaseObservation(
        image_hash=f"hash{idx:04d}" * 4,
        image_file=f"img_{idx}.jpg",
        subject="room",
        schema_version="1.0",
        prompt_version="1.0",
        observed_at=datetime.now().isoformat(),
        features=[ObservedFeature(**f) for f in features],
        forbidden_hints=forbidden_hints or [],
    )


class TestNotVisibleExclusion:
    """Test: 'not_visible' values are excluded from evidence counting."""

    def test_not_visible_not_counted_as_evidence(self):
        observations = [
            make_obs(0, [{"key": "wall_artwork", "type": "enum", "value": "not_visible", "category": "furniture", "confidence": 0.0}]),
            make_obs(1, [{"key": "wall_artwork", "type": "enum", "value": "not_visible", "category": "furniture", "confidence": 0.0}]),
            make_obs(2, [{"key": "wall_artwork", "type": "enum", "value": "not_visible", "category": "furniture", "confidence": 0.0}]),
            make_obs(3, [{"key": "wall_artwork", "type": "enum", "value": "not_visible", "category": "furniture", "confidence": 0.0}]),
        ]
        result = _pass2a(observations, AGGREGATION_KEYS, [], THRESHOLDS)
        # All "not_visible" → evidence_count=0 for all → not in any category (coverage=0 < weak_threshold)
        assert "wall_artwork" not in result["invariant_raw"]
        assert "wall_artwork" not in result["variable_raw"]
