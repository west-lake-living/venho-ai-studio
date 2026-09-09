from __future__ import annotations

import re

from validator_studio.naturalness.report import Violation


# The list is intentionally a small, editable seed.  Research facts and
# GuestAngle.concrete_details are added at call time so the gate stays useful
# outside one particular hotel project too.
DEFAULT_LOCAL_ANCHORS = (
    "Hồ Tây", "Tây Hồ", "Quảng An", "Từ Hoa", "Trích Sài", "Vệ Hồ",
    "Nguyễn Đình Thi", "Nhật Chiêu", "Đặng Thai Mai", "Phủ Tây Hồ",
    "Chùa Trấn Quốc", "Chùa Kim Liên", "Chợ Hoa Quảng Bá", "Ven Hồ Hotel",
    "Hà Nội", "Hanoi", "West Lake",
)
CONCRETE_NOUNS = (
    "ban công", "cửa sổ", "mặt hồ", "phố", "con đường", "xe máy", "xe đạp",
    "bát bún", "cốc cà phê", "ly cà phê", "ấm trà", "cuốn sách", "quầy lễ tân",
    "phòng", "giường", "rèm", "sàn gỗ", "rooftop", "lobby", "cây bàng",
    "hàng cây", "bến nước", "cầu", "mái ngói", "đèn đường", "chợ hoa",
)
NUMBER_OR_MEASURE = re.compile(
    r"(?<!\w)(?:\d+[\d.,]*\s*(?:giờ|h|phút|ngày|đêm|tháng|năm|km|m|phòng|tầng|%|đ|₫|đồng|người|bước)?)",
    flags=re.IGNORECASE,
)
TIME_MARK = re.compile(
    r"\b(?:\d{1,2}\s*(?:giờ|h)|thứ\s+[2-7]|thứ\s+bảy|sáng|trưa|chiều|tối|bình minh|hoàng hôn|mùa\s+\w+|tháng\s+\w+)\b",
    flags=re.IGNORECASE,
)


def _words(text: str) -> list[str]:
    return re.findall(r"[\wÀ-ỹĐđ]+", text, flags=re.UNICODE)


def _non_overlapping_occurrences(text: str, terms: tuple[str, ...]) -> list[str]:
    lowered = text.casefold()
    spans: list[tuple[int, int, str]] = []
    for term in sorted(terms, key=len, reverse=True):
        start = 0
        needle = term.casefold()
        while True:
            index = lowered.find(needle, start)
            if index < 0:
                break
            end = index + len(term)
            if not any(index < existing_end and end > existing_start for existing_start, existing_end, _ in spans):
                spans.append((index, end, term))
            start = index + 1
    return [term for _, _, term in sorted(spans)]


def specificity_anchors(text: str, *, concrete_details: list[str] | tuple[str, ...] = ()) -> list[str]:
    anchors: list[str] = []
    anchors.extend(_non_overlapping_occurrences(text, DEFAULT_LOCAL_ANCHORS))
    anchors.extend(_non_overlapping_occurrences(text, tuple(str(item) for item in concrete_details if str(item).strip())))
    anchors.extend(match.group(0) for match in NUMBER_OR_MEASURE.finditer(text))
    anchors.extend(match.group(0) for match in TIME_MARK.finditer(text))
    anchors.extend(_non_overlapping_occurrences(text, CONCRETE_NOUNS))
    return anchors


def specificity_score(text: str, *, concrete_details: list[str] | tuple[str, ...] = ()) -> float:
    words = _words(text)
    if not words:
        return 0.0
    return round(len(specificity_anchors(text, concrete_details=concrete_details)) * 100 / len(words), 2)


def check_specificity(
    text: str,
    *,
    concrete_details: list[str] | tuple[str, ...] = (),
    rewrite_threshold: float = 2.5,
    pass_threshold: float = 4.0,
) -> tuple[float, list[Violation]]:
    score = specificity_score(text, concrete_details=concrete_details)
    if score < rewrite_threshold:
        return score, [Violation(
            rule_id="SP-01",
            message=f"Mật độ chi tiết cụ thể quá thấp: {score:.2f} neo/100 từ.",
            suggestion="Bổ sung ít nhất 3 chi tiết trong GuestAngle: tên phố, giờ, số liệu có fact R3 hoặc vật thể quan sát được.",
            # Warning, not a hard REWRITE: on the labelled real-caption set
            # (2026-09-09) specificity density did not separate AI-sounding
            # from acceptable copy (medians 8.2 vs 7.9), and the anchor regex
            # scores repeated "Hồ Tây" as specificity. It also false-flags
            # genuine operations prose that talks about guests without street
            # names. Kept as a signal for the rewrite prompt, not a gate.
            severity="warning",
        )]
    if score < pass_threshold:
        return score, [Violation(
            rule_id="SP-02",
            message=f"Mật độ chi tiết cụ thể còn thấp: {score:.2f} neo/100 từ.",
            suggestion="Ưu tiên thêm một tên địa phương hoặc mốc thời gian nếu không làm câu gượng.",
            severity="warning",
        )]
    return score, []
