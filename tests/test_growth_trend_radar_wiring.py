from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_engine.trend_radar.application.fetch_saturday_candidates import fetch_and_score_saturday_candidates
from research_engine.trend_radar.classifiers.gemini_classifier import classify_candidates, classify_candidates_from_env
from research_engine.trend_radar.trend_candidate_store import TrendCandidateStore

_TREND_POLICY = {
    "relevance_dimensions": {
        "geographic": {"westlake": 1.0, "hanoi": 0.7, "vietnam": 0.4, "global": 0.1},
        "thematic": {"travel_stay": 1.0, "food_local": 0.8, "lifestyle_culture": 0.6, "seasonal_weather": 0.5, "unrelated": 0.0},
        "actionability": {"direct": 1.0, "adjacent": 0.6, "stretch": 0.2},
    },
    "min_score_to_saturday_lane": 0.6,
}
_SAFETY_POLICY = {
    "forbidden_trend_categories": ["politics_governance", "crime_scandal"],
    "required_intersection": ["hanoi_westlake_local", "seasonal_weather_nature"],
}


def _fake_client_response(classified: list[dict]) -> str:
    return json.dumps(classified, ensure_ascii=False)


def test_classify_candidates_merges_taxonomy_onto_raw_results() -> None:
    raw = [{"id": "t1", "title": "Sen Hồ Tây nở rộ", "snippet": "Mùa sen Hồ Tây đang nở đẹp", "source_uri": "https://x", "relevance_hint": 0.5}]
    classification = [
        {"id": "t1", "geographic": "westlake", "thematic": "seasonal_weather", "actionability": "direct",
         "type": "seasonal_nature", "brand_safety_category": "safe", "intersections": ["hanoi_westlake_local", "seasonal_weather_nature"]},
    ]
    client_fn = lambda **kwargs: _fake_client_response(classification)  # noqa: E731

    result = classify_candidates(raw, api_key="fake-key", client_fn=client_fn)

    assert len(result) == 1
    assert result[0]["title"] == "Sen Hồ Tây nở rộ"  # original field kept
    assert result[0]["geographic"] == "westlake"
    assert result[0]["type"] == "seasonal_nature"


def test_classify_candidates_drops_unclassified_ids_fail_closed() -> None:
    raw = [{"id": "t1", "title": "A", "snippet": ""}, {"id": "t2", "title": "B", "snippet": ""}]
    client_fn = lambda **kwargs: _fake_client_response(  # noqa: E731
        [{"id": "t1", "geographic": "westlake", "thematic": "travel_stay", "actionability": "direct",
          "type": "lifestyle_trend", "brand_safety_category": "safe", "intersections": ["hanoi_westlake_local"]}]
    )
    result = classify_candidates(raw, api_key="fake-key", client_fn=client_fn)
    assert [c["id"] for c in result] == ["t1"]  # t2 silently dropped, not defaulted


def test_classify_candidates_from_env_returns_empty_without_api_key(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert classify_candidates_from_env([{"id": "t1", "title": "x"}]) == []


def test_fetch_and_score_saturday_candidates_deduplicates_and_scores(tmp_path: Path) -> None:
    def fake_collect(query: str, *, api_key: str, **kwargs) -> list[dict]:
        return [{"id": "shared-id", "title": query, "snippet": "", "source_uri": "https://x", "relevance_hint": 0.5}]

    def fake_classify(candidates: list[dict]) -> list[dict]:
        return [
            {**c, "geographic": "westlake", "thematic": "travel_stay", "actionability": "direct",
             "type": "seasonal_nature", "brand_safety_category": "safe", "intersections": ["hanoi_westlake_local", "seasonal_weather_nature"]}
            for c in candidates
        ]

    result = fetch_and_score_saturday_candidates(
        tavily_api_key="fake",
        trend_policy=_TREND_POLICY,
        safety_policy=_SAFETY_POLICY,
        queries=["q1", "q2"],  # both queries return the same id -> must dedupe to 1
        collect_fn=fake_collect,
        classify_fn=fake_classify,
    )

    assert len(result) == 1
    assert result[0]["status"] == "needs_human_approval"
    assert result[0]["relevance_score"] >= 0.6


def test_fetch_and_score_saturday_candidates_rejects_forbidden_category(tmp_path: Path) -> None:
    def fake_collect(query: str, *, api_key: str, **kwargs) -> list[dict]:
        return [{"id": "bad-1", "title": query, "snippet": ""}]

    def fake_classify(candidates: list[dict]) -> list[dict]:
        return [
            {**c, "geographic": "westlake", "thematic": "seasonal_weather", "actionability": "direct",
             "type": "feature_story", "brand_safety_category": "crime_scandal", "intersections": ["hanoi_westlake_local"]}
            for c in candidates
        ]

    result = fetch_and_score_saturday_candidates(
        tavily_api_key="fake", trend_policy=_TREND_POLICY, safety_policy=_SAFETY_POLICY,
        queries=["q"], collect_fn=fake_collect, classify_fn=fake_classify,
    )
    assert result[0]["status"] == "rejected"
    assert result[0]["rejection_reason"] == "forbidden_trend_category"


def test_trend_candidate_store_merge_new_never_overwrites_approval(tmp_path: Path) -> None:
    store = TrendCandidateStore("venho_hotel", data_root=tmp_path)
    store.merge_new([{"id": "c1", "title": "A", "status": "needs_human_approval"}])
    store.approve("c1", approved_by="harry")

    # Re-scanning must not reset the approval back to False.
    store.merge_new([{"id": "c1", "title": "A (re-scanned)", "status": "needs_human_approval"}])

    candidate = next(c for c in store.load() if c["id"] == "c1")
    assert candidate["verified_by_human"] is True
    assert candidate["title"] == "A"  # untouched, not overwritten by the re-scan


def test_trend_candidate_store_list_eligible_excludes_unapproved_and_used(tmp_path: Path) -> None:
    store = TrendCandidateStore("venho_hotel", data_root=tmp_path)
    store.merge_new([
        {"id": "unapproved", "title": "A", "status": "needs_human_approval"},
        {"id": "approved", "title": "B", "status": "needs_human_approval"},
        {"id": "rejected", "title": "C", "status": "rejected"},
    ])
    store.approve("approved", approved_by="harry")
    store.approve("rejected", approved_by="harry")  # approving a rejected-status one still shouldn't surface it

    eligible_before = store.list_eligible_for_saturday()
    assert {c["id"] for c in eligible_before} == {"approved"}

    store.mark_used("approved")
    assert store.list_eligible_for_saturday() == []


def test_trend_candidate_store_approve_unknown_id_raises(tmp_path: Path) -> None:
    store = TrendCandidateStore("venho_hotel", data_root=tmp_path)
    try:
        store.approve("nope", approved_by="harry")
        assert False, "expected KeyError"
    except KeyError:
        pass


def test_a_rejected_candidate_can_never_reach_a_saturday_brief(tmp_path: Path) -> None:
    store = TrendCandidateStore(data_root=tmp_path)
    store.merge_new([{"id": "c1", "title": "Lễ hội đã qua", "status": "needs_human_approval"}])
    store.approve("c1", approved_by="harry")

    store.reject("c1", rejected_by="harry")

    assert store.list_eligible_for_saturday() == []
    assert store.load()[0]["verified_by_human"] is False


def test_rejecting_survives_the_next_scan_instead_of_being_re_proposed(tmp_path: Path) -> None:
    """A real delete would come back every Friday -- merge_new dedupes on id."""
    store = TrendCandidateStore(data_root=tmp_path)
    store.merge_new([{"id": "c1", "title": "Lễ hội đã qua", "status": "needs_human_approval"}])
    store.reject("c1", rejected_by="harry")

    assert store.merge_new([{"id": "c1", "title": "Lễ hội đã qua", "status": "needs_human_approval"}]) == 0
    assert store.load()[0]["status"] == "rejected"


def test_rejecting_an_unknown_candidate_is_an_error_not_a_silent_no_op(tmp_path: Path) -> None:
    with pytest.raises(KeyError):
        TrendCandidateStore(data_root=tmp_path).reject("nope", rejected_by="harry")
