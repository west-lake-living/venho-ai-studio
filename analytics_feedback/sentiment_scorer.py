from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


DEFAULT_GUARDRAILS = {
    "negative_spike_threshold": 0.15,
    "minimum_comments_for_alert": 10,
    "critical_keywords": {
        "vi": ["ban", "bẩn", "lua dao", "lừa đảo", "hoan tien", "hoàn tiền", "tho lo", "thô lỗ", "mat an toan", "mất an toàn", "hoi", "hôi"],
        "en": ["dirty", "scam", "refund", "rude", "unsafe"],
    },
    "alert_target": "M04_AUTOMATION_STUDIO",
}


@dataclass(frozen=True)
class SentimentResult:
    total_comments: int
    negative_comments: int
    negative_comment_ratio: float
    negative_sentiment_spike: bool
    critical_keywords_triggered: List[str]


def score_comments(comments: Iterable[str], guardrails: Dict[str, object] | None = None) -> SentimentResult:
    config = {**DEFAULT_GUARDRAILS, **(guardrails or {})}
    keywords_by_lang = config.get("critical_keywords", {})
    keywords = [word for values in keywords_by_lang.values() for word in values]
    comments_list = list(comments)
    triggered: List[str] = []
    negative_count = 0
    for comment in comments_list:
        lowered = comment.casefold()
        found = [word for word in keywords if word.casefold() in lowered]
        if found:
            negative_count += 1
            triggered.extend(found)
    total = len(comments_list)
    ratio = round(negative_count / total, 3) if total else 0.0
    spike = ratio >= float(config["negative_spike_threshold"]) and total >= int(config["minimum_comments_for_alert"])
    return SentimentResult(
        total_comments=total,
        negative_comments=negative_count,
        negative_comment_ratio=ratio,
        negative_sentiment_spike=spike,
        critical_keywords_triggered=sorted(set(triggered)),
    )
