from __future__ import annotations

import re

from validator_studio.naturalness.report import Violation

# Real production captions leak raw scene-DNA tokens into the published
# Vietnamese copy: hex colour codes and English scene descriptors straight out
# of the image/environment prompt ("muted jade-teal #4E8FA0 calm reflective not
# tropical blue", "urban lakeside with moderate vegetation and distant
# cityscape").  In the labelled calibration set this appeared in 14/34 AI-
# sounding captions and 0/14 acceptable ones — a clean deterministic signal.
_HEX_COLOR = re.compile(r"#[0-9A-Fa-f]{6}\b")
_ENGLISH_SCENE = re.compile(
    r"\b(calm|reflective|moderate|muted|jade[- ]?teal|overcast|partly\s+cloudy|"
    r"low[- ]?rise|urban\s+lakeside|vegetation|cityscape|tropical\s+blue|"
    r"clear\s+sky|soft\s+light|distant)\b",
    re.IGNORECASE,
)


def check_dna_leak(text: str) -> list[Violation]:
    hex_hits = _HEX_COLOR.findall(text)
    english = sorted({match.lower() for match in _ENGLISH_SCENE.findall(text)})
    if not hex_hits and len(english) < 2:
        return []
    detail = ", ".join(hex_hits + english)
    return [Violation(
        rule_id="DNA-LEAK",
        message=f"Lộ token DNA cảnh vào bài đăng: {detail}",
        excerpt=detail,
        suggestion=(
            "Bỏ mã màu hex và các từ mô tả tiếng Anh (calm, moderate, muted, "
            "jade-teal…). Tả cảnh bằng tiếng Việt đời thường, cụ thể."
        ),
    )]
