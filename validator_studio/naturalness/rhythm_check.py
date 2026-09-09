from __future__ import annotations

import re
from statistics import pvariance

from validator_studio.naturalness.report import Violation


def check_rhythm(text: str, *, minimum_words: int = 80, variance_threshold: float = 15.0) -> list[Violation]:
    word_count = len(re.findall(r"\w+", text, flags=re.UNICODE))
    if word_count < minimum_words:
        return []
    lengths = [len(re.findall(r"\w+", sentence)) for sentence in re.split(r"(?<=[.!?])\s+|\n+", text) if sentence.strip()]
    if len(lengths) < 3 or pvariance(lengths) >= variance_threshold:
        return []
    return [Violation(
        rule_id="RH-01",
        message=f"Phương sai độ dài câu quá thấp: {pvariance(lengths):.2f}.",
        suggestion="Xen một câu ngắn có nhịp tự nhiên với câu mô tả dài hơn.",
    )]
