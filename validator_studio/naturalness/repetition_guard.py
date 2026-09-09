from __future__ import annotations

import re
from difflib import SequenceMatcher

from validator_studio.naturalness.report import Violation


def _tokens(text: str) -> list[str]:
    # Do not remove Vietnamese tone marks.  Removing them turns unrelated
    # words into false matches ("ma" vs "má" is a real example).
    return re.findall(r"[\wÀ-ỹĐđ]+", text.casefold(), flags=re.UNICODE)


# Every hotel post shares a scaffold -- hashtag block, tracking URL, brand
# name, the "nhắn cho ... để xem phòng" CTA.  Comparing that scaffold makes
# the repetition guard fire on 100% of real captions (measured on the labelled
# calibration set).  Strip it before the n-gram comparison so RP-01 sees only
# the body prose.
_SCAFFOLD = re.compile(
    r"https?://\S+"
    r"|#[\wÀ-ỹĐđ]+"
    r"|(?i:ven\s*h[ồo]\s*hotel)"
    r"|(?i:(?:nhắn|liên hệ|inbox|hotline|zalo)[^.\n]*?(?:phòng|đặt phòng|book)[^.\n]*)",
)


def _body_tokens(text: str) -> list[str]:
    return _tokens(_SCAFFOLD.sub(" ", text))


def _ngrams(tokens: list[str], size: int) -> set[tuple[str, ...]]:
    return {tuple(tokens[index:index + size]) for index in range(max(0, len(tokens) - size + 1))}


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text) if part.strip()]


def _structure(text: str) -> tuple[int, str, str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    lowered = text.casefold()
    cta_position = "none"
    if re.search(r"\b(?:nhắn|liên hệ|đặt phòng|xem phòng|book|inbox)\b", lowered):
        cta_position = "last" if _sentences(text) and re.search(
            r"\b(?:nhắn|liên hệ|đặt phòng|xem phòng|book|inbox)\b", _sentences(text)[-1].casefold()
        ) else "body"
    ending = "question" if text.rstrip().endswith("?") else "invitation" if cta_position == "last" else "observation"
    return len(paragraphs), cta_position, ending


def check_repetition(candidate: str, recent_posts: list[str] | tuple[str, ...]) -> list[Violation]:
    recent = [str(post).strip() for post in recent_posts if str(post).strip()]
    if not recent:
        return []
    violations: list[Violation] = []
    # 6-grams on the de-scaffolded body: on the calibration set a shared
    # 5-gram was still mostly boilerplate, a shared 6-gram of real prose is a
    # genuine reuse.
    candidate_grams = _ngrams(_body_tokens(candidate), 6)
    matching_posts = []
    for index, post in enumerate(recent[:12]):
        overlap = candidate_grams & _ngrams(_body_tokens(post), 6)
        if len(overlap) >= 3:
            matching_posts.append((index, post, overlap))
    if matching_posts:
        index, post, overlap = matching_posts[0]
        sample = " ".join(next(iter(overlap)))
        violations.append(Violation(
            rule_id="RP-01",
            message=f"Trùng ít nhất 3 chuỗi 6 từ với bài gần đây (bài #{index + 1}).",
            excerpt=sample,
            suggestion="Giữ fact nhưng viết lại câu và đổi cách dẫn vào.",
        ))

    candidate_sentences = _sentences(candidate)
    candidate_opener = candidate_sentences[0] if candidate_sentences else candidate
    for index, post in enumerate(recent[:12]):
        prior_sentences = _sentences(post)
        if not prior_sentences:
            continue
        similarity = SequenceMatcher(None, _tokens(candidate_opener), _tokens(prior_sentences[0])).ratio()
        if similarity >= 0.75:
            violations.append(Violation(
                rule_id="RP-02",
                message=f"Mở bài quá giống bài gần đây (similarity={similarity:.2f}, bài #{index + 1}).",
                excerpt=candidate_opener,
                suggestion="Bắt đầu ở một thời điểm, vật thể hoặc tuyến phố khác.",
            ))
            break

    candidate_structure = _structure(candidate)
    same_structure = sum(_structure(post) == candidate_structure for post in recent[:12])
    if same_structure >= 3:
        violations.append(Violation(
            rule_id="RP-03",
            message="Vân cấu trúc bài lặp lại ít nhất 3 lần trong 12 bài gần nhất.",
            suggestion="Đổi số đoạn, vị trí CTA hoặc kiểu kết; không chỉ thay vài từ.",
            # Warning, not error: a 4-post/week feed with a house style will
            # reuse paragraph count + CTA placement legitimately.  On the
            # labelled set this fired on 6/14 acceptable captions.
            severity="warning",
        ))

    candidate_phrases = _ngrams(_body_tokens(candidate), 4)
    phrase_counts: dict[tuple[str, ...], int] = {}
    for post in recent[:12]:
        for phrase in _ngrams(_body_tokens(post), 4):
            phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1
    repeated_phrases = [phrase for phrase in candidate_phrases if phrase_counts.get(phrase, 0) >= 3]
    if repeated_phrases:
        sample = " ".join(repeated_phrases[0])
        violations.append(Violation(
            rule_id="RP-04",
            message="Có cụm bốn từ đặc trưng đã xuất hiện ít nhất 3 lần.",
            excerpt=sample,
            suggestion="Thay cụm mô tả này bằng chi tiết riêng của angle hiện tại.",
            severity="warning",
        ))
    return violations
