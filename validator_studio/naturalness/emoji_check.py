from __future__ import annotations

import re

from validator_studio.naturalness.report import Violation


EMOJI = re.compile(
    r"[\U0001F300-\U0001FAFF\u2600-\u27BF]",
    flags=re.UNICODE,
)


def check_emoji(text: str) -> list[Violation]:
    violations: list[Violation] = []
    emojis = EMOJI.findall(text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(emojis) > 1 and all(EMOJI.match(line) for line in lines if line):
        violations.append(Violation(
            rule_id="EM-01",
            message="Emoji xuất hiện theo mẫu máy móc ở đầu mọi dòng/bullet.",
            suggestion="Chỉ dùng emoji khi nó có vai trò tự nhiên trong câu; có thể bỏ toàn bộ.",
        ))
    words = re.findall(r"\w+", text, flags=re.UNICODE)
    if len(emojis) > 1 and len(emojis) / max(len(words), 1) > 1 / 40:
        violations.append(Violation(
            rule_id="EM-02",
            message="Mật độ emoji vượt 1 emoji trên 40 từ.",
            suggestion="Giảm emoji xuống mức cần thiết cho nền tảng, không dùng để chia ý cơ học.",
        ))
    for match in EMOJI.finditer(text):
        before = text[:match.start()].rstrip()
        after = text[match.end():].lstrip()
        if before and after and after[0] not in ".,!?\n":
            violations.append(Violation(
                rule_id="EM-03",
                message="Emoji nằm giữa câu.",
                excerpt=text[max(0, match.start() - 30):match.end() + 30],
                suggestion="Đưa emoji về cuối câu/đoạn hoặc bỏ nếu không cần.",
                severity="warning",
            ))
            break
    return violations
