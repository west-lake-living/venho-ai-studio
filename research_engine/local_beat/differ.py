from __future__ import annotations

import hashlib
import re
from difflib import SequenceMatcher
from typing import Iterable

from research_engine.local_beat.entities import BeatEntity, BeatItem, BeatStatus, SearchResult, WeekSnapshot


STATUS_KEYWORDS: tuple[tuple[BeatStatus, tuple[str, ...]], ...] = (
    (BeatStatus.AFFECTING_GUESTS, ("rào đường", "ảnh hưởng giao thông", "ùn tắc", "tiếng ồn", "hạn chế đi lại")),
    (BeatStatus.IN_PROGRESS, ("đang thi công", "đang triển khai", "khởi công", "thi công")),
    (BeatStatus.COMPLETED, ("hoàn thành", "đưa vào sử dụng", "khánh thành")),
    (BeatStatus.STALLED, ("chậm tiến độ", "đình trệ", "tạm dừng")),
    (BeatStatus.SCHEDULED, ("dự kiến", "khởi công vào", "bắt đầu từ", "lịch triển khai")),
    (BeatStatus.APPROVED, ("được duyệt", "phê duyệt", "chủ trương đầu tư")),
    (BeatStatus.RUMORED, ("đề xuất", "đang xem xét", "tin đồn")),
)


def infer_status(result: SearchResult) -> tuple[BeatStatus, str]:
    haystack = f"{result.title} {result.snippet} {result.content}".casefold()
    for status, keywords in STATUS_KEYWORDS:
        for keyword in keywords:
            if keyword.casefold() in haystack:
                return status, f"matched: {keyword}"
    return BeatStatus.RUMORED, "no lifecycle keyword matched"


def _content_prefix(result: SearchResult) -> str:
    return re.sub(r"\s+", " ", f"{result.title} {result.snippet} {result.content}").strip()[:1200]


def _item_id(entity_id: str, result: SearchResult) -> str:
    return f"beat-{entity_id}-{hashlib.sha256(result.url.encode('utf-8')).hexdigest()[:12]}"


def _mentions_entity(entity: BeatEntity, result: SearchResult) -> bool:
    prefix = " ".join(_content_prefix(result).casefold().split()[:200])
    names = (entity.name, *entity.queries)
    return any(str(name).casefold() in prefix for name in names)


def _meaningful_change(current: BeatItem, previous: BeatItem) -> bool:
    old = f"{previous.title} {previous.snippet} {previous.content}"
    new = f"{current.title} {current.snippet} {current.content}"
    return SequenceMatcher(None, old.casefold(), new.casefold()).ratio() < 0.85


def diff_week(current: list[BeatItem], previous_snapshot: WeekSnapshot | None) -> list[BeatItem]:
    """Return new URL/content/state changes, excluding unchanged recaps."""
    previous_by_url = {item.url: item for item in (previous_snapshot.items if previous_snapshot else ())}
    result: list[BeatItem] = []
    for item in current:
        previous = previous_by_url.get(item.url)
        if previous is None or _meaningful_change(item, previous) or item.status != previous.status:
            result.append(item)
    return result


def build_beat_items(entity: BeatEntity, results: Iterable[SearchResult], *, detected_at: str) -> list[BeatItem]:
    items: list[BeatItem] = []
    seen_urls: set[str] = set()
    for result in results:
        if result.url in seen_urls or not _mentions_entity(entity, result):
            continue
        seen_urls.add(result.url)
        status, reason = infer_status(result)
        items.append(BeatItem(
            id=_item_id(entity.id, result), entity_id=entity.id, entity_name=entity.name,
            url=result.url, title=result.title, snippet=result.snippet, content=result.content,
            published_at=result.published_at, detected_at=detected_at, status=status,
            status_reason=reason, changed=True,
        ))
    return items
