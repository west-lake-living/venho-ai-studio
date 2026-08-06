"""Brand Safety Gate coverage — v3.1 master plan DoD #19 requires >=15 test
cases proving every forbidden category is blocked at the gate. Part 7.4
calls this "the highest-risk section of the whole system" and TR-D3 makes
human_approval mandatory forever, even for passing candidates.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import yaml

from research_engine.trend_radar.application.scan_trends import scan_trends
from research_engine.trend_radar.domain.brand_safety import BrandSafetyGate

CONFIG_ROOT = Path("config/projects/venho_hotel/research")

FORBIDDEN_CATEGORIES = [
    "politics_governance",
    "disaster_accident",
    "death_tragedy",
    "crime_scandal",
    "celebrity_personal",
    "health_crisis",
    "religion_ethnicity",
    "competitor_negative",
    "social_conflict",
]

REQUIRED_INTERSECTIONS = [
    "travel_accommodation",
    "hanoi_westlake_local",
    "food_culinary",
    "seasonal_weather_nature",
    "culture_festival_positive",
]


def _policy() -> dict:
    return yaml.safe_load((CONFIG_ROOT / "brand_safety.yaml").read_text(encoding="utf-8"))


def _trend_policy() -> dict:
    return yaml.safe_load((CONFIG_ROOT / "trend_policy.yaml").read_text(encoding="utf-8"))


@pytest.mark.parametrize("category", FORBIDDEN_CATEGORIES)
def test_forbidden_category_is_blocked_even_with_required_intersection(category: str) -> None:
    """Kill switch takes priority: a forbidden category is blocked even when
    it also intersects a required (otherwise-safe) theme."""
    gate = BrandSafetyGate(_policy())
    allowed, reason = gate.evaluate(category, ["travel_accommodation"])
    assert allowed is False
    assert reason == "forbidden_trend_category"


@pytest.mark.parametrize("intersection", REQUIRED_INTERSECTIONS)
def test_non_forbidden_category_passes_with_each_required_intersection(intersection: str) -> None:
    gate = BrandSafetyGate(_policy())
    allowed, reason = gate.evaluate("lifestyle_culture", [intersection])
    assert allowed is True
    assert reason == "passed"


def test_non_forbidden_category_blocked_without_any_required_intersection() -> None:
    gate = BrandSafetyGate(_policy())
    allowed, reason = gate.evaluate("lifestyle_culture", ["unrelated_topic"])
    assert allowed is False
    assert reason == "missing_required_brand_intersection"


def test_non_forbidden_category_blocked_with_empty_intersections() -> None:
    gate = BrandSafetyGate(_policy())
    allowed, reason = gate.evaluate("lifestyle_culture", [])
    assert allowed is False
    assert reason == "missing_required_brand_intersection"


def test_multiple_intersections_pass_if_any_one_matches_required() -> None:
    gate = BrandSafetyGate(_policy())
    allowed, reason = gate.evaluate(
        "lifestyle_culture", ["unrelated_topic", "hanoi_westlake_local", "another_unrelated"]
    )
    assert allowed is True
    assert reason == "passed"


def test_category_matching_is_exact_not_fuzzy() -> None:
    """'politics' should NOT match the forbidden 'politics_governance' entry —
    the gate must not silently under- or over-block on partial strings."""
    gate = BrandSafetyGate(_policy())
    allowed, reason = gate.evaluate("politics", ["travel_accommodation"])
    assert allowed is True
    assert reason == "passed"


def test_empty_category_is_not_forbidden_but_still_needs_intersection() -> None:
    gate = BrandSafetyGate(_policy())
    allowed, reason = gate.evaluate("", [])
    assert allowed is False
    assert reason == "missing_required_brand_intersection"


def test_gate_with_no_required_intersection_configured_passes_any_non_forbidden() -> None:
    """If a policy sets an empty required_intersection list, nothing should be
    rejected on that basis — only the forbidden-category kill switch applies."""
    gate = BrandSafetyGate({"forbidden_trend_categories": ["crime_scandal"], "required_intersection": []})
    allowed, reason = gate.evaluate("random_category", [])
    assert allowed is True
    assert reason == "passed"


def test_real_project_policy_still_lists_all_nine_forbidden_categories() -> None:
    """Guards against someone silently trimming the kill-switch list in
    config/projects/venho_hotel/research/brand_safety.yaml."""
    policy = _policy()
    assert set(policy["forbidden_trend_categories"]) == set(FORBIDDEN_CATEGORIES)
    assert policy["human_approval"] == "mandatory"


# --- Integration: scan_trends() end-to-end using the real project policy ---


def test_scan_trends_rejects_every_forbidden_category_end_to_end() -> None:
    candidates = [
        {"id": f"cand-{category}", "brand_safety_category": category, "intersections": ["travel_accommodation"]}
        for category in FORBIDDEN_CATEGORIES
    ]
    results = scan_trends(candidates, _trend_policy(), _policy())
    assert len(results) == len(FORBIDDEN_CATEGORIES)
    for result in results:
        assert result["status"] == "rejected"
        assert result["rejection_reason"] == "forbidden_trend_category"


def test_scan_trends_never_returns_auto_approved_status() -> None:
    """TR-D3: the Saturday special lane must never auto-approve. scan_trends'
    only positive outcome is 'needs_human_approval', never a status that
    could be mistaken for an already-approved/publishable state."""
    candidates = [
        {
            "id": "good",
            "brand_safety_category": "lifestyle_culture",
            "intersections": ["hanoi_westlake_local"],
            "geographic": "westlake",
            "thematic": "travel_stay",
            "actionability": "direct",
        },
        {"id": "bad", "brand_safety_category": "crime_scandal", "intersections": ["hanoi_westlake_local"]},
    ]
    results = scan_trends(candidates, _trend_policy(), _policy())
    statuses = {r["id"]: r["status"] for r in results}
    assert statuses["good"] == "needs_human_approval"
    assert statuses["bad"] == "rejected"
    assert "approved" not in {r["status"] for r in results}


def test_scan_trends_low_relevance_score_rejected_even_if_brand_safe() -> None:
    candidates = [
        {
            "id": "low-relevance",
            "brand_safety_category": "lifestyle_culture",
            "intersections": ["hanoi_westlake_local"],
            "geographic": "global",
            "thematic": "unrelated",
            "actionability": "stretch",
        }
    ]
    results = scan_trends(candidates, _trend_policy(), _policy())
    assert results[0]["status"] == "rejected"


# --- Stale candidates (2026-08-07) -----------------------------------------


def _live_candidate(**overrides: object) -> dict:
    return {
        "id": "cand",
        "brand_safety_category": "lifestyle_culture",
        "intersections": ["hanoi_westlake_local"],
        "geographic": "westlake",
        "thematic": "travel_stay",
        "actionability": "direct",
        **overrides,
    }


def test_scan_trends_rejects_a_candidate_whose_event_already_ended() -> None:
    """The one Harry was looking at on 2026-08-07: brand-safe, well scored,
    and six weeks expired."""
    candidates = [
        _live_candidate(
            id="lotus",
            title="Lễ hội Sen Hà Nội diễn ra từ ngày 26-28/6 tại các không gian ven Hồ Tây",
        )
    ]
    results = scan_trends(candidates, _trend_policy(), _policy(), today=date(2026, 8, 7))
    assert results[0]["status"] == "rejected"
    assert results[0]["rejection_reason"] == "stale_dated"


def test_scan_trends_reads_the_snippet_not_just_the_title() -> None:
    """A news index dates itself in the body, never in the headline."""
    candidates = [
        _live_candidate(
            id="sputnik",
            title="Hồ Tây - tin tức mới nhất hôm nay",
            snippet="Chiêm ngưỡng show drones\n\n5 Tháng Ba 2024, 08:49\n\nHàng tấn cá\n\n17 Tháng Mười Một 2021, 14:15",
        )
    ]
    results = scan_trends(candidates, _trend_policy(), _policy(), today=date(2026, 8, 7))
    assert results[0]["status"] == "rejected"
    assert results[0]["rejection_reason"] == "stale_dated"


def test_scan_trends_keeps_an_upcoming_event_and_an_undated_evergreen() -> None:
    """Both halves matter: the filter must not eat next month's festival, and
    it must not eat the undated cafe guides that carry the evergreen pool."""
    candidates = [
        _live_candidate(id="upcoming", title="Lễ hội áo dài Hồ Tây ngày 12-14/9"),
        _live_candidate(id="evergreen", title="25 quán cafe view Hồ Tây đẹp"),
    ]
    results = scan_trends(candidates, _trend_policy(), _policy(), today=date(2026, 8, 7))
    assert {r["id"]: r["status"] for r in results} == {
        "upcoming": "needs_human_approval",
        "evergreen": "needs_human_approval",
    }


def test_a_stale_candidate_is_still_reported_as_forbidden_when_it_is_both() -> None:
    """Brand safety is the more serious finding and must not be masked by a
    date -- the audit trail for a blocked category has to say so."""
    candidates = [
        _live_candidate(id="both", brand_safety_category="crime_scandal", title="Vụ án ngày 26-28/6")
    ]
    results = scan_trends(candidates, _trend_policy(), _policy(), today=date(2026, 8, 7))
    assert results[0]["rejection_reason"] == "forbidden_trend_category"
