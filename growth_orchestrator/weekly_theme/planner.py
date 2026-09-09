from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import yaml

from growth_orchestrator.weekly_theme.diversity_rules import CADENCE, DEFAULT_ROTATION, choose_angle_types
from growth_orchestrator.weekly_theme.models import AngleType, ThemeAngle, WeeklyThemePlan


def _entry_text(entry: Any) -> str:
    if isinstance(entry, str):
        return entry.strip()
    if isinstance(entry, dict):
        return str(entry.get("title") or entry.get("name") or entry.get("text") or entry.get("topic") or "").strip()
    return str(entry).strip()


def _entry_details(entry: Any) -> tuple[str, ...]:
    if isinstance(entry, dict):
        details = entry.get("concrete_details") or entry.get("details") or []
        if isinstance(details, str):
            details = [details]
        if details:
            return tuple(str(item).strip() for item in details if str(item).strip())
    text = _entry_text(entry)
    # These are only seed details for planning.  They are not citable facts;
    # M01/R3 still owns factual claims downstream.
    candidates = re.findall(r"(?:Hồ Tây|Tây Hồ|Quảng An|Từ Hoa|Trích Sài|Vệ Hồ|Nguyễn Đình Thi|Phủ Tây Hồ|\d+(?:h| giờ| phút)?)", text, re.I)
    details = list(dict.fromkeys(candidates))
    if len(details) < 2:
        details.extend(["Hồ Tây", "Ven Hồ Hotel"])
    return tuple(details[:4])


def _pick_source(
    local_beats: Iterable[Any], seasonal: Iterable[Any], trends: Iterable[Any], evergreen: Iterable[Any]
) -> tuple[str, str, Any, list[str]]:
    local = [item for item in local_beats if _entry_text(item)]
    if local:
        item = local[0]
        return "local_beat", _entry_text(item), item, []
    seasonal_items = [item for item in seasonal if _entry_text(item)]
    if seasonal_items:
        item = seasonal_items[0]
        return "seasonal", _entry_text(item), item, []
    trend_items = [item for item in trends if _entry_text(item)]
    if trend_items:
        item = trend_items[0]
        return "trend_radar", _entry_text(item), item, []
    evergreen_items = [item for item in evergreen if _entry_text(item)]
    if evergreen_items:
        item = evergreen_items[0]
        return "evergreen", _entry_text(item), item, ["Tuần này dùng chất liệu evergreen; cần bổ sung beat địa phương cho tuần sau."]
    return "evergreen", "Một lát cắt đời sống quanh Hồ Tây", "Hồ Tây", ["Tuần này thiếu chất liệu tươi, chỉ dựng được 3 góc; cần người duyệt bổ sung chất liệu."]


def _banned_openers(recent_posts: Iterable[str], limit: int = 12) -> list[str]:
    result: list[str] = []
    for post in list(recent_posts)[:limit]:
        first = re.split(r"(?<=[.!?])\s+|\n+", str(post).strip(), maxsplit=1)[0].strip()
        if first and first not in result:
            result.append(first)
    return result


def _banned_phrases(recent_posts: Iterable[str], limit: int = 4) -> list[str]:
    counts: dict[str, int] = {}
    for post in list(recent_posts)[: max(12, limit * 3)]:
        words = re.findall(r"[\wÀ-ỹĐđ]+", str(post).casefold(), flags=re.UNICODE)
        for index in range(max(0, len(words) - 3 + 1)):
            phrase = " ".join(words[index:index + 3])
            if len(phrase) >= 8:
                counts[phrase] = counts.get(phrase, 0) + 1
    return [phrase for phrase, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])) if count >= 2][:20]


def plan_week(
    iso_week: str | None = None,
    *,
    local_beats: Iterable[Any] = (),
    seasonal: Iterable[Any] = (),
    trends: Iterable[Any] = (),
    evergreen: Iterable[Any] = (),
    recent_plans: Iterable[dict] = (),
    recent_posts: Iterable[str] = (),
    available_angle_types: Iterable[AngleType] = DEFAULT_ROTATION,
) -> WeeklyThemePlan:
    """Build one weekly spine and up to four different angle types.

    Inputs are already collected/approved upstream.  This planner does not
    fetch news, call an LLM, or promote evidence.
    """
    week = iso_week or date.today().isocalendar().week
    iso_week_value = str(week) if isinstance(week, str) else f"{date.today().isocalendar().year}-W{int(week):02d}"
    recent_plan_list = list(recent_plans)
    local_list, seasonal_list, trend_list, evergreen_list = list(local_beats), list(seasonal), list(trends), list(evergreen)
    source, spine, source_entry, warnings = _pick_source(local_list, seasonal_list, trend_list, evergreen_list)
    has_source = any(_entry_text(item) for item in (*local_list, *seasonal_list, *trend_list, *evergreen_list))
    candidate_types = list(available_angle_types) if has_source else list(available_angle_types)[:3]
    types, type_warnings = choose_angle_types(available=candidate_types)
    warnings.extend(type_warnings)

    angles: dict[str, ThemeAngle] = {}
    recent_used_by_day: dict[str, set[str]] = {}
    for previous in recent_plan_list[-3:]:
        for weekday, raw_angle in (previous.get("angles") or {}).items():
            value = raw_angle.get("angle_type") if isinstance(raw_angle, dict) else getattr(raw_angle, "angle_type", None)
            if value:
                recent_used_by_day.setdefault(str(weekday), set()).add(str(getattr(value, "value", value)))
    assigned: set[AngleType] = set()
    for index, weekday in enumerate(CADENCE):
        if index >= len(types):
            break
        angle_type = next(
            (
                candidate for offset in range(len(types))
                for candidate in (types[(index + offset) % len(types)],)
                if candidate not in assigned and candidate.value not in recent_used_by_day.get(weekday, set())
            ),
            next((candidate for candidate in types if candidate not in assigned), types[index]),
        )
        assigned.add(angle_type)
        details = _entry_details(source_entry)
        angle_title = {
            AngleType.PRACTICAL: f"Điều khách cần biết về {spine}",
            AngleType.OBSERVATION: f"Một quan sát ở {spine}",
            AngleType.GUIDE: f"Gợi ý đi quanh {spine}",
            AngleType.STORY: f"Một câu chuyện nhỏ từ {spine}",
            AngleType.CONTEXT: f"{spine} đang thay đổi ra sao",
            AngleType.SERVICE: f"Ven Hồ hỗ trợ chuyến đi quanh {spine}",
        }[angle_type]
        angles[weekday] = ThemeAngle(
            weekday=weekday,
            angle_type=angle_type,
            title=angle_title,
            premise=spine,
            concrete_details=details,
            source=source,
            guest_question=f"Khách sẽ cần biết gì trước khi đến {spine}?",
            what_we_can_say=f"Chia sẻ góc nhìn thực dụng của Ven Hồ quanh {spine}.",
            what_we_cannot_claim=("Số liệu, mốc tiến độ hoặc tác động chưa có fact R3 active.",),
        )
    if len(angles) < 4 and "Tuần này thiếu chất liệu" not in " ".join(warnings):
        warnings.append(f"Tuần thiếu chất liệu, chỉ dựng được {len(angles)} góc khác loại.")

    return WeeklyThemePlan(
        iso_week=iso_week_value,
        spine=spine,
        spine_source=source,  # type: ignore[arg-type]
        angles=angles,  # type: ignore[arg-type]
        banned_openers=_banned_openers(recent_posts),
        banned_phrases=_banned_phrases(recent_posts),
        warnings=list(dict.fromkeys(warnings)),
    )


def load_angle_types(path: Path | None = None) -> dict[str, dict[str, str]]:
    source = path or Path(__file__).with_name("angle_types.yaml")
    payload = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    return payload.get("types", {})
