"""Phase 7 — Observation cache tests.

Verifies:
  - _cache_path key format: {hash}_{schema_id}_{schema_version}_{prompt_version}
  - Same inputs → same cache path (stable key)
  - Different schema_id / schema_version / prompt_version → different path
  - _load_cache returns None for missing file
  - _load_cache returns BaseObservation from valid cached JSON
  - _load_cache returns None for corrupt JSON
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from knowledge_studio.vision.pass1_observe import _cache_path, _load_cache
from knowledge_studio.vision.schemas.base import BaseObservation

BASE_DIR = Path(__file__).parent.parent


class _SimpleSubjectDef:
    schema_id = "universal"
    observation_cls = BaseObservation


def _minimal_obs(**kwargs) -> BaseObservation:
    defaults = dict(
        image_hash="abc123",
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
# TestCacheKeyFormat
# ---------------------------------------------------------------------------

class TestCacheKeyFormat:
    def test_cache_path_contains_image_hash(self, tmp_path):
        path = _cache_path(tmp_path, "abc123", "universal", "1.0", "1.0")
        assert "abc123" in path.name

    def test_cache_path_contains_schema_id(self, tmp_path):
        path = _cache_path(tmp_path, "abc123", "universal", "1.0", "1.0")
        assert "universal" in path.name

    def test_cache_path_contains_schema_version(self, tmp_path):
        path = _cache_path(tmp_path, "abc123", "universal", "1.0", "1.0")
        assert "1.0" in path.name

    def test_cache_path_is_json(self, tmp_path):
        path = _cache_path(tmp_path, "abc123", "universal", "1.0", "1.0")
        assert path.suffix == ".json"

    def test_same_inputs_same_path(self, tmp_path):
        p1 = _cache_path(tmp_path, "abc", "universal", "1.0", "1.0")
        p2 = _cache_path(tmp_path, "abc", "universal", "1.0", "1.0")
        assert p1 == p2

    def test_different_schema_id_different_path(self, tmp_path):
        p1 = _cache_path(tmp_path, "abc", "universal", "1.0", "1.0")
        p2 = _cache_path(tmp_path, "abc", "room", "1.0", "1.0")
        assert p1 != p2

    def test_different_schema_version_different_path(self, tmp_path):
        p1 = _cache_path(tmp_path, "abc", "universal", "1.0", "1.0")
        p2 = _cache_path(tmp_path, "abc", "universal", "1.1", "1.0")
        assert p1 != p2

    def test_different_prompt_version_different_path(self, tmp_path):
        p1 = _cache_path(tmp_path, "abc", "universal", "1.0", "1.0")
        p2 = _cache_path(tmp_path, "abc", "universal", "1.0", "1.1")
        assert p1 != p2

    def test_different_image_hash_different_path(self, tmp_path):
        p1 = _cache_path(tmp_path, "hash_A", "universal", "1.0", "1.0")
        p2 = _cache_path(tmp_path, "hash_B", "universal", "1.0", "1.0")
        assert p1 != p2


# ---------------------------------------------------------------------------
# TestLoadCache
# ---------------------------------------------------------------------------

class TestLoadCache:
    def test_load_cache_returns_none_for_missing_file(self, tmp_path):
        cache_file = tmp_path / "nonexistent.json"
        result = _load_cache(cache_file, _SimpleSubjectDef())
        assert result is None

    def test_load_cache_returns_observation_for_valid_file(self, tmp_path):
        obs = _minimal_obs(image_hash="abc123", provider="mock")
        cache_file = tmp_path / "test.json"
        cache_file.write_text(obs.model_dump_json(), encoding="utf-8")
        result = _load_cache(cache_file, _SimpleSubjectDef())
        assert result is not None
        assert result.image_hash == "abc123"
        assert result.provider == "mock"

    def test_load_cache_returns_none_for_corrupt_json(self, tmp_path):
        cache_file = tmp_path / "corrupt.json"
        cache_file.write_text("{ invalid json }", encoding="utf-8")
        result = _load_cache(cache_file, _SimpleSubjectDef())
        assert result is None

    def test_load_cache_returns_none_for_wrong_schema(self, tmp_path):
        cache_file = tmp_path / "wrong_schema.json"
        cache_file.write_text(json.dumps({"unexpected_key": "value"}), encoding="utf-8")
        result = _load_cache(cache_file, _SimpleSubjectDef())
        assert result is None

    def test_cached_observation_preserves_features(self, tmp_path):
        from knowledge_studio.vision.schemas.base import ObservedFeature
        feat = ObservedFeature(key="floor", type="enum", value="hardwood", category="materials", confidence=0.9)
        obs = _minimal_obs(features=[feat])
        cache_file = tmp_path / "test_feat.json"
        cache_file.write_text(obs.model_dump_json(), encoding="utf-8")
        result = _load_cache(cache_file, _SimpleSubjectDef())
        assert result is not None
        assert result.features[0].key == "floor"
