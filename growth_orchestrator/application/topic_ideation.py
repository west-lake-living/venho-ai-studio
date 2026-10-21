from __future__ import annotations

"""Fresh topic ideas per lane, so posts stop cycling the same 3-10 lines.

Why (2026-10-21 audit): each lane posts once a week from a static pool of
10/8/10/3 hand-written lines under a 60-day exact-text cooldown, so Monday
and Friday repeated every 7-8 weeks and Saturday's "a quiet weekend morning
walk around West Lake" went out 4 times. The lines were also generic moods
("mau nuoc Ho Tay thay doi theo tung gio") rather than something specific to
this week.

Gemini Flash proposes ~8 concrete angles for the lane from the month's
seasonal hooks, the hotel's real features and approved upcoming events, told
which topics already went out. Ideas too close to a topic posted in the last
IDEA_DEDUPE_DAYS are dropped in code. Every resulting draft still goes
through the copy validator and Harry's approval.

Opt-in (GROWTH_TOPIC_IDEATION=1 + GEMINI_API_KEY): tests and local runs never
call the API. Best-effort: any failure returns [] and the lane falls back to
its curated pool exactly as before.
"""

import json
import os
import re
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Optional

import yaml

IDEA_DEDUPE_DAYS = 120
IDEAS_PER_CALL = 8
DEFAULT_MODEL = os.environ.get("GEMINI_TOPIC_MODEL", "gemini-flash-latest")

# Words shared by nearly every topic here; left in, any two lines look alike.
_GENERIC = {
    "ho", "tay", "ha", "noi", "ven", "hotel", "khach", "san", "o", "va", "cua", "trong", "tren", "mot",
    "nhung", "cac", "voi", "cho", "the", "la", "khi", "luc", "ngay", "tuan", "cuoi", "dau", "gio",
    "west", "lake", "at", "the", "a", "of", "and", "in",
}

_SYSTEM_PROMPT = """Bạn lên ý tưởng chủ đề bài đăng Facebook/Instagram cho Ven Hồ Hotel, khách sạn boutique 12 phòng ở 181 Nguyễn Đình Thi, ven Hồ Tây, Hà Nội. Câu hỏi gốc của mọi bài: "Sống bên Hồ Tây hôm nay là như thế nào?"

Trả về JSON array gồm đúng {n} chuỗi, mỗi chuỗi là MỘT chủ đề tiếng Việt có dấu, 6-14 từ, cụ thể: một khoảnh khắc, một cảnh, một món, một việc nên làm, gắn với tháng này hoặc với lane. Không chung chung kiểu "không khí Hồ Tây thật đẹp".

Không được:
- bịa tên quán, tên doanh nghiệp, giá, khuyến mãi, con số; chỉ nhắc địa danh công cộng nổi tiếng (phủ Tây Hồ, chùa Trấn Quốc, đường Thanh Niên, Quảng Bá, Nhật Tân, Quảng An, Trúc Bạch) hoặc sự kiện có trong danh sách được đưa
- nói về khách sạn bằng chi tiết KHÔNG có trong "hotel_angles" (vd ban công, bể bơi, nhà hàng, spa, bữa sáng) -- chỉ dùng đúng các chi tiết được đưa
- lặp lại hay đổi chữ một chủ đề trong "already_posted"
- nói về khách sạn khác, chính trị, tin tiêu cực

Không thêm text ngoài JSON."""


def ideation_enabled() -> bool:
    return os.environ.get("GROWTH_TOPIC_IDEATION") == "1" and bool(os.environ.get("GEMINI_API_KEY"))


def _tokens(text: str) -> set[str]:
    folded = unicodedata.normalize("NFD", str(text or "").replace("đ", "d").replace("Đ", "D"))
    folded = "".join(ch for ch in folded if unicodedata.category(ch) != "Mn").lower()
    return {token for token in re.findall(r"[a-z0-9]+", folded) if token not in _GENERIC and len(token) > 1}


def too_similar(a: str, b: str, *, threshold: float = 0.5) -> bool:
    """Overlap against the shorter topic's meaningful words."""
    tokens_a, tokens_b = _tokens(a), _tokens(b)
    if not tokens_a or not tokens_b:
        return False
    return len(tokens_a & tokens_b) / min(len(tokens_a), len(tokens_b)) >= threshold


def recent_topic_texts(publications: list[dict[str, Any]], *, today: date, days: int = IDEA_DEDUPE_DAYS) -> list[str]:
    cutoff = today - timedelta(days=days)
    texts: list[str] = []
    for pub in publications:
        try:
            created = datetime.fromisoformat(str(pub.get("created_at") or "")).date()
        except ValueError:
            continue
        topic = pub.get("topic")
        if isinstance(topic, str) and created >= cutoff and topic not in texts:
            texts.append(topic)
    return texts


def load_seasonal_calendar(config_root: Path, project: str) -> dict[str, Any]:
    path = config_root / project / "content" / "seasonal_calendar.yaml"
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}


def _default_client_fn(*, model: str, system: str, contents: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(system_instruction=system, temperature=0.9, response_mime_type="application/json"),
    )
    return response.text


def ideate_topics(
    lane_config: dict[str, Any],
    *,
    target_date: date,
    calendar: dict[str, Any],
    recent_topics: list[str],
    upcoming_events: Optional[list[str]] = None,
    client_fn: Optional[Callable[..., str]] = None,
    model: str = DEFAULT_MODEL,
) -> list[str]:
    """Up to IDEAS_PER_CALL new topic lines for one lane, already filtered
    against `recent_topics` and each other. [] on any failure."""
    curated = [t for t in lane_config.get("topics", []) if isinstance(t, str)]
    for group in lane_config.get("special_topics") or []:
        curated.extend(t for t in group.get("topics", []) if isinstance(t, str))
    request = {
        "lane": lane_config.get("name") or lane_config.get("id"),
        "lane_id": lane_config.get("id"),
        "post_date": target_date.isoformat(),
        "seasonal_hooks_this_month": (calendar.get("months") or {}).get(target_date.month, []),
        "hotel_angles": calendar.get("hotel_angles", []),
        "approved_upcoming_events": upcoming_events or [],
        "tone_examples": curated[:6],
        "already_posted": recent_topics[:60],
    }
    try:
        raw = (client_fn or _default_client_fn)(
            model=model,
            system=_SYSTEM_PROMPT.format(n=IDEAS_PER_CALL),
            contents=json.dumps(request, ensure_ascii=False),
        ).strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        ideas = json.loads(raw)
    except Exception:  # noqa: BLE001 - ideation is best-effort, curated pool is the fallback
        return []

    kept: list[str] = []
    for idea in ideas if isinstance(ideas, list) else []:
        if not isinstance(idea, str):
            continue
        idea = " ".join(idea.split()).strip(" .")
        if not (3 <= len(idea.split()) <= 20):
            continue
        if any(too_similar(idea, seen) for seen in [*recent_topics, *kept]):
            continue
        kept.append(idea)
    return kept[:IDEAS_PER_CALL]
