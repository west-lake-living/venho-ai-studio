"""Phase 8 — rglob recursive media loader, max_completion_tokens API fix, gpt-5.5 model upgrade."""

import inspect
import json
from pathlib import Path

import pytest

from core.media_loader import load_images

BASE_DIR = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Recursive media loader — rglob (§media_loader fix)
# ---------------------------------------------------------------------------

class TestRecursiveMediaLoader:
    def test_finds_images_in_top_level(self, tmp_path):
        (tmp_path / "a.jpg").write_bytes(b"fake")
        (tmp_path / "b.png").write_bytes(b"fake")
        result = load_images(tmp_path)
        assert len(result) == 2

    def test_finds_images_in_nested_subfolder(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "img.jpg").write_bytes(b"fake")
        result = load_images(tmp_path)
        assert len(result) == 1
        assert result[0].name == "img.jpg"

    def test_finds_images_across_multiple_subfolders(self, tmp_path):
        (tmp_path / "sub1").mkdir()
        (tmp_path / "sub2").mkdir()
        (tmp_path / "sub1" / "a.jpeg").write_bytes(b"fake")
        (tmp_path / "sub2" / "b.png").write_bytes(b"fake")
        (tmp_path / "top.jpg").write_bytes(b"fake")
        result = load_images(tmp_path)
        assert len(result) == 3

    def test_ignores_non_image_files(self, tmp_path):
        (tmp_path / "note.txt").write_bytes(b"text")
        (tmp_path / "img.jpg").write_bytes(b"fake")
        result = load_images(tmp_path)
        assert len(result) == 1

    def test_empty_folder_raises(self, tmp_path):
        with pytest.raises(ValueError, match="Không tìm thấy ảnh"):
            load_images(tmp_path)

    def test_results_are_sorted(self, tmp_path):
        for name in ["c.jpg", "a.jpg", "b.jpg"]:
            (tmp_path / name).write_bytes(b"fake")
        result = load_images(tmp_path)
        names = [p.name for p in result]
        assert names == sorted(names)

    def test_room_subfolders_found(self):
        """Regression: assets/raw/room/ has VenHo-room-1/ and ViewHo-room-2/ subfolders."""
        room_dir = BASE_DIR / "assets" / "raw" / "room"
        if not room_dir.exists():
            pytest.skip("assets/raw/room/ not present")
        result = load_images(room_dir)
        assert len(result) >= 2, "Should find images across both room subfolders"


# ---------------------------------------------------------------------------
# max_completion_tokens API fix (§openai_provider fix)
# ---------------------------------------------------------------------------

class TestOpenAIProviderParam:
    def test_source_uses_max_completion_tokens(self):
        provider_path = BASE_DIR / "providers" / "openai_provider.py"
        source = provider_path.read_text(encoding="utf-8")
        assert "max_completion_tokens" in source, \
            "openai_provider.py must use max_completion_tokens (not max_tokens)"

    def test_source_does_not_use_deprecated_max_tokens(self):
        provider_path = BASE_DIR / "providers" / "openai_provider.py"
        source = provider_path.read_text(encoding="utf-8")
        lines_with_max_tokens = [
            line.strip() for line in source.splitlines()
            if "max_tokens" in line and "max_completion_tokens" not in line
        ]
        assert not lines_with_max_tokens, \
            f"Found deprecated max_tokens usage: {lines_with_max_tokens}"


# ---------------------------------------------------------------------------
# Model upgrade — gpt-5.5 (§settings.json fix)
# ---------------------------------------------------------------------------

class TestModelConfig:
    def _load_settings(self) -> dict:
        settings_path = BASE_DIR / "config" / "settings.json"
        return json.loads(settings_path.read_text(encoding="utf-8"))

    def test_openai_model_is_gpt_5_5(self):
        settings = self._load_settings()
        assert settings["openai_model"] == "gpt-5.5", \
            f"Expected gpt-5.5, got: {settings.get('openai_model')}"

    def test_claude_model_unchanged(self):
        settings = self._load_settings()
        assert "claude" in settings["claude_model"].lower(), \
            "claude_model should still reference a Claude model"

    def test_settings_has_required_keys(self):
        settings = self._load_settings()
        for key in ("openai_model", "claude_model", "batch_size", "providers"):
            assert key in settings, f"Missing key in settings.json: {key}"
