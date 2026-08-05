from __future__ import annotations

import json
import os
from typing import Any, Callable, Optional

# The taxonomy scan_trends/score_relevance/BrandSafetyGate expect on every
# candidate -- see config/projects/venho_hotel/research/trend_policy.yaml
# and brand_safety.yaml. Raw Tavily results (title/snippet/url only) don't
# carry any of this; this is the missing classification step scan_trends'
# own comments flagged as "downstream, not here" but nothing actually built.
_GEOGRAPHIC = ["westlake", "hanoi", "vietnam", "global"]
_THEMATIC = ["travel_stay", "food_local", "lifestyle_culture", "seasonal_weather", "unrelated"]
_ACTIONABILITY = ["direct", "adjacent", "stretch"]
_SPECIAL_LANE_TYPES = ["seasonal_nature", "cultural_event", "lifestyle_trend", "feature_story"]
_REQUIRED_INTERSECTIONS = [
    "travel_accommodation", "hanoi_westlake_local", "food_culinary",
    "seasonal_weather_nature", "culture_festival_positive",
]
_FORBIDDEN_CATEGORIES = [
    "politics_governance", "disaster_accident", "death_tragedy", "crime_scandal",
    "celebrity_personal", "health_crisis", "religion_ethnicity", "competitor_negative", "social_conflict",
]

_SYSTEM_PROMPT = f"""Bạn phân loại kết quả tìm kiếm web thành taxonomy cố định cho Ven Ho Hotel (khách sạn ở Tây Hồ, Hà Nội).

Với MỖI item đầu vào, trả về đúng các field sau (không thêm field khác):
- geographic: một trong {_GEOGRAPHIC}
- thematic: một trong {_THEMATIC}
- actionability: một trong {_ACTIONABILITY}
- type: một trong {_SPECIAL_LANE_TYPES} (seasonal_nature = mùa/thiên nhiên Hồ Tây, cultural_event = sự kiện văn hoá cụ thể cần xác minh, lifestyle_trend = xu hướng đời sống, feature_story = không khớp loại nào)
- brand_safety_category: nếu nội dung thuộc một trong {_FORBIDDEN_CATEGORIES} thì ghi đúng tên đó; ngược lại ghi "safe"
- intersections: danh sách con của {_REQUIRED_INTERSECTIONS} mô tả nội dung này liên quan gì đến khách sạn/Hồ Tây (rỗng nếu không liên quan gì)

Trả về JSON array, mỗi phần tử có "id" (giữ nguyên id đầu vào) + 6 field trên. Không thêm text ngoài JSON."""


def classify_candidates(
    candidates: list[dict[str, Any]],
    *,
    api_key: str,
    model: str = "claude-sonnet-5",
    client_fn: Optional[Callable[..., Any]] = None,
) -> list[dict[str, Any]]:
    """Classify raw Tavily results into the taxonomy scan_trends() needs.

    One batched call for all candidates (cheaper than one call per result).
    `client_fn` is injectable so tests never hit the real Anthropic API --
    matches content_studio.generators.claude_generator's convention ("Never
    call this in pytest"). Returns the original candidate dicts merged with
    the classification fields; a candidate Claude's response is missing or
    malformed for is dropped (fail-closed -- an unclassified candidate must
    never silently reach scan_trends with default/empty taxonomy values,
    since that could accidentally pass the brand-safety gate).
    """
    if not candidates:
        return []
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in environment")

    if client_fn is None:
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise RuntimeError("anthropic package not installed — run: pip install anthropic") from exc
        client = Anthropic(api_key=api_key)
        client_fn = lambda **kwargs: client.messages.create(**kwargs)  # noqa: E731

    payload = [{"id": c["id"], "title": c.get("title", ""), "snippet": c.get("snippet", "")} for c in candidates]
    response = client_fn(
        model=model,
        max_tokens=4096,
        temperature=0,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    classified_by_id = {}
    for entry in json.loads(raw):
        entry_id = entry.get("id")
        if entry_id:
            classified_by_id[entry_id] = entry

    results = []
    for candidate in candidates:
        classification = classified_by_id.get(candidate["id"])
        if classification is None:
            continue
        results.append({**candidate, **{k: v for k, v in classification.items() if k != "id"}})
    return results


def classify_candidates_from_env(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Best-effort wrapper: returns [] (not an exception) if ANTHROPIC_API_KEY
    is unset or the call fails, matching the graceful-degradation convention
    already used for OPENAI_API_KEY/GOOGLE_DRIVE_TOKEN_JSON elsewhere in this
    codebase -- a Trend Radar hiccup must never block the regular daily_cycle
    text/image pipeline it feeds a Saturday topic suggestion into.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return []
    try:
        return classify_candidates(candidates, api_key=api_key)
    except Exception:  # noqa: BLE001 - best-effort, see docstring
        return []
