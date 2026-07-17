from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence


MOCK_OBSERVATION = {
    "features": [
        {"key": "window_frame", "type": "enum", "value": "black_aluminum", "category": "structure", "confidence": 0.95},
        {"key": "window_layout", "type": "enum", "value": "grid_2x2", "category": "structure", "confidence": 0.90},
        {"key": "ceiling", "type": "enum", "value": "decorative_molding", "category": "structure", "confidence": 0.85},
        {"key": "floor", "type": "enum", "value": "not_visible", "category": "structure", "confidence": 0.0},
        {"key": "wall_color", "type": "free", "value": "light gray-white", "category": "structure", "confidence": 0.92},
        {"key": "room_shape", "type": "enum", "value": "rectangular", "category": "structure", "confidence": 0.88},
        {"key": "bed_size", "type": "enum", "value": "double", "category": "furniture", "confidence": 0.90},
        {"key": "bed_headboard", "type": "enum", "value": "wooden", "category": "furniture", "confidence": 0.95},
        {"key": "bedding_color", "type": "free", "value": "white", "category": "furniture", "confidence": 0.98},
        {"key": "desk", "type": "enum", "value": "present_with_mirror", "category": "furniture", "confidence": 0.92},
        {"key": "chairs", "type": "enum", "value": "two_wooden", "category": "furniture", "confidence": 0.88},
        {"key": "wardrobe", "type": "enum", "value": "not_visible", "category": "furniture", "confidence": 0.0},
        {"key": "wood_tone", "type": "enum", "value": "dark_reddish_brown", "category": "materials", "confidence": 0.93},
        {"key": "curtain_color", "type": "free", "value": "gray-brown", "category": "materials", "confidence": 0.85},
        {"key": "lighting_condition", "type": "enum", "value": "natural_daylight", "category": "lighting", "confidence": 0.90},
        {"key": "lake_view_visible", "type": "enum", "value": "yes", "category": "view", "confidence": 0.95},
        {"key": "style_category", "type": "enum", "value": "boutique_vietnamese", "category": "atmosphere", "confidence": 0.88},
        {"key": "hotel_tier", "type": "enum", "value": "mid_range", "category": "atmosphere", "confidence": 0.85},
        {"key": "wall_artwork", "type": "enum", "value": "three_floral_prints", "category": "furniture", "confidence": 0.92},
    ],
    "notable_features": ["black aluminum grid window frames", "three framed floral prints on wall"],
    "uncertainty": [],
    "forbidden_hints": ["no floor-to-ceiling glass wall", "no marble interior"],
}


class MockVisionProvider:
    """Offline mock provider — returns deterministic schema-valid output without API calls."""

    def __init__(self, model: str = "mock", temperature: float = 0.0) -> None:
        self.model = model
        self.temperature = temperature

    def analyze(self, image_path: Path, system_prompt: str) -> dict[str, Any]:
        return dict(MOCK_OBSERVATION)

    def analyze_many(
        self, image_paths: Sequence[Path], system_prompt: str, text_prompt: str = ""
    ) -> dict[str, Any]:
        return dict(MOCK_OBSERVATION)

    def synthesize(self, system_prompt: str, user_content: str) -> list[dict[str, Any]]:
        """Parse the input JSON and echo back canonical = first value for each key."""
        import json as _json
        try:
            items = _json.loads(user_content)
            return [
                {"key": item["key"], "canonical": item["values"][0] if item.get("values") else item["key"]}
                for item in items
                if isinstance(item, dict) and "key" in item
            ]
        except Exception:
            return []
