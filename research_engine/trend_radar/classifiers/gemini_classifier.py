from __future__ import annotations

import json
import os
from typing import Any, Callable, Optional

# Same taxonomy as the (now retired) claude_classifier -- see
# config/projects/venho_hotel/research/trend_policy.yaml and brand_safety.yaml.
# Switched to Gemini Flash on 2026-08-05 (Harry: Anthropic cost too high for
# a startup's classification-only workload; content generation elsewhere in
# the codebase stays on Claude -- this swap is scoped to Trend Radar only).
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

DEFAULT_MODEL = os.environ.get("GEMINI_TREND_MODEL", "gemini-flash-latest")


def classify_candidates(
    candidates: list[dict[str, Any]],
    *,
    api_key: str,
    model: str = DEFAULT_MODEL,
    client_fn: Optional[Callable[..., Any]] = None,
) -> list[dict[str, Any]]:
    """Classify raw Tavily results into the taxonomy scan_trends() needs.

    One batched call for all candidates. `client_fn` is injectable so tests
    never hit the real Gemini API. Returns the original candidate dicts
    merged with the classification fields; a candidate Gemini's response is
    missing or malformed for is dropped (fail-closed -- an unclassified
    candidate must never silently reach scan_trends with default/empty
    taxonomy values, since that could accidentally pass the brand-safety
    gate).
    """
    if not candidates:
        return []
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in environment")

    if client_fn is None:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise RuntimeError(
                "google-genai package not installed — run: pip install 'venho-ai-studio[gemini]'"
            ) from exc
        client = genai.Client(api_key=api_key)

        def client_fn(*, model: str, system: str, contents: str) -> str:  # noqa: ANN001
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    temperature=0,
                    response_mime_type="application/json",
                ),
            )
            return response.text

    payload = [{"id": c["id"], "title": c.get("title", ""), "snippet": c.get("snippet", "")} for c in candidates]
    raw = client_fn(
        model=model,
        system=_SYSTEM_PROMPT,
        contents=json.dumps(payload, ensure_ascii=False),
    ).strip()
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
    """Best-effort wrapper: returns [] (not an exception) if GEMINI_API_KEY
    is unset or the call fails, matching the graceful-degradation convention
    already used for OPENAI_API_KEY/GOOGLE_DRIVE_TOKEN_JSON elsewhere in this
    codebase -- a Trend Radar hiccup must never block the regular daily_cycle
    text/image pipeline it feeds a Saturday topic suggestion into.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return []
    try:
        return classify_candidates(candidates, api_key=api_key)
    except Exception:  # noqa: BLE001 - best-effort, see docstring
        return []
