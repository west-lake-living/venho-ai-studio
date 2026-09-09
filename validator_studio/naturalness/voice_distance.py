from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

from validator_studio.naturalness.report import Violation


@dataclass(frozen=True)
class VoiceDistance:
    distance: float
    sample_count: int
    warning: bool


def _words(text: str) -> list[str]:
    return re.findall(r"[\wÀ-ỹĐđ]+", text, flags=re.UNICODE)


def _features(text: str) -> tuple[float, float, float, float]:
    words = _words(text)
    if not words:
        return 0.0, 0.0, 0.0, 0.0
    sentences = [chunk for chunk in re.split(r"[.!?\n]+", text) if chunk.strip()]
    sentence_length = mean([len(_words(chunk)) for chunk in sentences]) if sentences else 0.0
    sino_vietnamese = sum(1 for word in words if word.casefold() in {
        "trải", "nghiệm", "không", "gian", "hành", "trình", "dịch", "vụ", "địa", "điểm",
        "khoảnh", "khắc", "tinh", "tế", "cảm", "xúc",
    }) / len(words)
    adjectives = sum(1 for word in words if word.casefold() in {
        "đẹp", "yên", "bình", "tuyệt", "vời", "ấm", "cúng", "nhẹ", "nhàng", "gọn", "gàng",
        "thân", "thiện", "tử", "tế", "chậm", "thật",
    }) / len(words)
    first_person = sum(1 for word in words if word.casefold() in {"mình", "tôi", "chúng", "ta", "bọn", "em"}) / len(words)
    return sentence_length, sino_vietnamese, adjectives, first_person


def measure_voice_distance(candidate: str, corpus_root: Path | None = None) -> VoiceDistance | None:
    if corpus_root is None or not corpus_root.exists():
        return None
    samples = [path.read_text(encoding="utf-8") for path in sorted(corpus_root.glob("*.md")) if path.name.lower() != "readme.md"]
    if not samples:
        return None
    target = _features(candidate)
    baseline = tuple(mean(values) for values in zip(*[_features(sample) for sample in samples]))
    # Normalised, descriptive distance; this is advisory while the corpus is
    # still small and is never a hard gate.
    distance = round(sum(abs(a - b) / max(abs(b), 1.0) for a, b in zip(target, baseline)) / 4, 3)
    return VoiceDistance(distance=distance, sample_count=len(samples), warning=distance > 0.65)


def voice_distance_violations(candidate: str, corpus_root: Path | None = None) -> tuple[float | None, list[Violation]]:
    result = measure_voice_distance(candidate, corpus_root)
    if result is None or not result.warning:
        return (result.distance if result else None), []
    return result.distance, [Violation(
        rule_id="VC-01",
        message=f"Khoảng cách thống kê tới Voice Corpus cao: {result.distance:.3f} ({result.sample_count} mẫu).",
        suggestion="Tham khảo 2–3 mẫu cùng AngleType; giữ câu cụt, nhịp rẽ ngang và đại từ tự nhiên nếu phù hợp.",
        severity="warning",
    )]
