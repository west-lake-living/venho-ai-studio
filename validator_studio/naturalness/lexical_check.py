from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from validator_studio.naturalness.report import Violation


RULES_PATH = Path(__file__).with_name("lexical_rules.yaml")


def load_lexical_rules(path: Path | None = None) -> dict[str, list[str]]:
    source = path or RULES_PATH
    payload: Any = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    return {key: [str(value) for value in payload.get(key, [])] for key in (
        "banned_openers", "banned_phrases", "banned_connectors", "banned_closers"
    )}


def _normalise(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()


def _contains_connector(text: str, phrase: str) -> bool:
    normalized = _normalise(text)
    parts = [part.strip() for part in phrase.split("...") if part.strip()]
    if len(parts) == 1:
        return parts[0] in normalized
    pattern = r"\s+".join(re.escape(part) + r".*?" for part in parts[:-1]) + re.escape(parts[-1])
    return re.search(pattern, normalized, flags=re.DOTALL) is not None


def _words(text: str) -> list[str]:
    return re.findall(r"[\wÀ-ỹĐđ]+", text, flags=re.UNICODE)


def _excerpt(text: str, needle: str) -> str:
    index = text.casefold().find(needle.casefold())
    if index < 0:
        return text[:120].strip()
    return text[max(0, index - 35): index + len(needle) + 55].strip()


def check_lexical(text: str, *, rules_path: Path | None = None) -> list[Violation]:
    rules = load_lexical_rules(rules_path)
    normalized = _normalise(text)
    violations: list[Violation] = []

    opener = _normalise(" ".join(_words(text)[:15]))
    for phrase in rules["banned_openers"]:
        if _normalise(phrase) in opener:
            violations.append(Violation(
                rule_id="LX-OPEN",
                message=f"Mở bài dùng cụm bị cấm: {phrase}",
                excerpt=_excerpt(text, phrase),
                suggestion="Mở bằng một quan sát địa điểm, vật thể hoặc thời điểm cụ thể.",
            ))

    for phrase in rules["banned_phrases"]:
        if _normalise(phrase) in normalized:
            violations.append(Violation(
                rule_id="LX-PHRASE",
                message=f"Dùng sáo ngữ: {phrase}",
                excerpt=_excerpt(text, phrase),
                suggestion="Thay tính từ chung bằng chi tiết tạo ra cảm giác đó.",
            ))

    for phrase in rules["banned_connectors"]:
        if _contains_connector(text, phrase):
            violations.append(Violation(
                rule_id="LX-CONNECTOR",
                message=f"Dùng cấu trúc nối quen thuộc: {phrase}",
                excerpt=_excerpt(text, phrase.split("...")[0].strip()),
                suggestion="Tách thành hai câu có quan sát hoặc hành động cụ thể.",
            ))

    tail = _normalise(" ".join(_words(text)[-20:]))
    for phrase in rules["banned_closers"]:
        if _normalise(phrase) in tail:
            violations.append(Violation(
                rule_id="LX-CLOSER",
                message=f"Kết bài dùng lời mời chung chung: {phrase}",
                excerpt=_excerpt(text, phrase),
                suggestion="Kết bằng giờ, địa chỉ, cách đi/đặt phòng hoặc một quan sát cụ thể.",
            ))
    return violations
