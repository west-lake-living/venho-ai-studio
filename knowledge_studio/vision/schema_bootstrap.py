from __future__ import annotations

"""Schema Bootstrap — generate a starter YAML schema from sample images.

Usage:
  from knowledge_studio.vision.schema_bootstrap import bootstrap
  bootstrap(image_paths=[...], client=client, subject_name="new_subject", output_path=Path("config/..."))
"""

from pathlib import Path
import re

import yaml

from shared.logging import log
from shared.vision.client import VisionClient
from shared.vision.image_loader import load_images


BOOTSTRAP_PROMPT = """You are a schema design assistant for a visual DNA system.

Given a sample image, identify the key visual features that would be useful to track
consistently across many images of the same subject.

For each feature:
1. Give it a short snake_case key name (e.g. window_frame, wall_color)
2. Decide if it's "enum" (a fixed set of values) or "free" (open text)
3. For enum keys, list the most likely values you can observe

Return ONLY valid JSON, no preamble:

{
  "suggested_keys": [
    {"key": "feature_name", "type": "enum", "values": ["value1", "value2", "other", "not_visible"]},
    {"key": "another_feature", "type": "free"}
  ]
}

Focus on features that:
- Are consistently visible across different images of this subject
- Help distinguish this subject from others of a similar type
- Are factual, not subjective
- Can be precisely described
"""

VALID_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")
VALID_VALUE_RE = re.compile(r"^[a-z0-9_]+$")
VALID_TYPES = {"enum", "free"}


def _normalize_value(value: object) -> str:
    """Return a stable English-like enum token or an empty string if invalid."""
    if not isinstance(value, str):
        return ""
    token = value.strip().lower().replace("-", "_").replace(" ", "_")
    token = re.sub(r"_+", "_", token)
    if not token.isascii() or not VALID_VALUE_RE.match(token):
        return ""
    return token


def _normalize_item(item: dict) -> dict | None:
    key = item.get("key", "")
    if not isinstance(key, str):
        return None
    key = key.strip()
    if not VALID_KEY_RE.match(key):
        return None

    item_type = item.get("type", "free")
    if item_type not in VALID_TYPES:
        item_type = "free"

    normalized = {"key": key, "type": item_type}
    if item_type == "enum":
        values: list[str] = []
        for value in item.get("values", []):
            normalized_value = _normalize_value(value)
            if normalized_value and normalized_value not in values:
                values.append(normalized_value)
        if "not_visible" not in values:
            values.append("not_visible")
        normalized["values"] = values
    return normalized


def bootstrap(
    image_paths: list[Path],
    client: VisionClient,
    subject_name: str,
    output_path: Path,
    display_name: str = "",
    description: str = "",
    max_sample: int = 3,
) -> Path:
    """Analyze sample images and generate a starter schema YAML.

    The user should review and edit the output before using it for Pass 1.
    """
    sample = image_paths[:max_sample]
    log(f"Schema Bootstrap — analyzing {len(sample)} sample images for '{subject_name}'…")

    all_keys: dict[str, dict] = {}

    for img_path in sample:
        log(f"  Sampling {img_path.name}…")
        raw = client.analyze_image(img_path, BOOTSTRAP_PROMPT)
        for item in raw.get("suggested_keys", []):
            normalized = _normalize_item(item)
            if normalized is None:
                continue
            key = normalized["key"]
            if key not in all_keys:
                all_keys[key] = normalized
            else:
                # Merge enum values
                existing_values = all_keys[key].get("values", [])
                for v in normalized.get("values", []):
                    if v not in existing_values:
                        existing_values.append(v)

    schema = {
        "schema_id": subject_name,
        "schema_version": "1.0",
        "subject": subject_name,
        "display_name": display_name or subject_name.replace("_", " ").title(),
        "description": description or f"Auto-bootstrapped schema for {subject_name}",
        "status": "draft",
        "approved_for_pass1": False,
        "review_notes": [
            "Human review required before this schema can be used by Pass 1.",
            "Confirm fixed keys, type enum/free, and English enum values.",
            "Set approved_for_pass1: true after approval.",
        ],
        "aggregation_keys": list(all_keys.values()),
        "forbidden_defaults": [],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        yaml.dump(schema, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )

    log(f"  → Schema saved: {output_path}")
    log(f"  → {len(all_keys)} suggested keys. REVIEW and set approved_for_pass1: true before use.")
    return output_path


def bootstrap_from_dir(
    image_dir: Path,
    client: VisionClient,
    subject_name: str,
    output_path: Path,
    **kwargs,
) -> Path:
    images = load_images(image_dir)
    if not images:
        raise FileNotFoundError(f"No images found in: {image_dir}")
    return bootstrap(image_paths=images, client=client, subject_name=subject_name, output_path=output_path, **kwargs)
