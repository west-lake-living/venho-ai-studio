from __future__ import annotations

from pathlib import Path

import yaml


def _read_sample(path: Path) -> tuple[str | None, str]:
    text = path.read_text(encoding="utf-8").strip()
    angle_type = None
    if text.startswith("---\n") and "\n---" in text[4:]:
        _, raw, body = text.split("---", 2)
        metadata = yaml.safe_load(raw) or {}
        angle_type = str(metadata.get("angle_type")) if metadata.get("angle_type") else None
        text = body.strip()
    return angle_type, text


def load_voice_exemplars(
    *,
    corpus_root: Path = Path("data/voice_corpus/samples"),
    angle_type: str | None = None,
    limit: int = 3,
) -> list[str]:
    """Load a small few-shot set; an empty operator corpus is valid."""
    if not corpus_root.exists():
        return []
    typed: list[str] = []
    untyped: list[str] = []
    for path in sorted(corpus_root.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        sample_angle, body = _read_sample(path)
        if not body:
            continue
        if angle_type and sample_angle == angle_type:
            typed.append(body)
        elif not sample_angle:
            untyped.append(body)
    return (typed + untyped)[:limit]
