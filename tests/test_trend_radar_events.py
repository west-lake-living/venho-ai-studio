from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from research_engine.trend_radar.application.event_clusters import cluster_events, same_event
from research_engine.trend_radar.application.fetch_saturday_candidates import fetch_and_score_saturday_candidates
from research_engine.trend_radar.application.scan_trends import scan_trends
from research_engine.trend_radar.classifiers.gemini_classifier import classify_candidates
from research_engine.trend_radar.collectors.news_rss import collect_google_news, headline_id
from research_engine.trend_radar.collectors.official_pages import collect_official_page
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
    "required_intersection": ["hanoi_westlake_local", "culture_festival_positive"],
}
_TODAY = date(2026, 10, 1)

_RSS = """<?xml version="1.0" encoding="UTF-8"?><rss><channel>
<item><title>Hà Nội dự kiến bắn 900 giàn pháo hoa tại hồ Tây tối 10/10 - VTV.vn</title>
<link>https://news.google.com/rss/articles/a1</link><pubDate>Mon, 28 Sep 2026 03:00:00 GMT</pubDate><source url="https://vtv.vn">VTV.vn</source></item>
<item><title>Tin cũ về Hồ Tây - Báo X</title>
<link>https://news.google.com/rss/articles/old</link><pubDate>Mon, 01 Jun 2026 03:00:00 GMT</pubDate><source url="https://x">Báo X</source></item>
</channel></rss>"""


def _event(id_: str, name: str, start: str | None, end: str | None = None, **extra) -> dict:
    return {
        "id": id_, "title": name, "source_uri": f"https://news/{id_}", "source_name": "Báo", "published_at": None,
        "geographic": "hanoi", "thematic": "lifestyle_culture", "actionability": "adjacent",
        "type": "cultural_event", "brand_safety_category": "safe",
        "intersections": ["hanoi_westlake_local", "culture_festival_positive"],
        "is_event": True, "event_name": name, "event_start": start, "event_end": end or start,
        "venue": "Hồ Tây", "westlake_area": True, **extra,
    }


def test_google_news_collector_strips_newsroom_and_drops_old_items() -> None:
    seen_urls: list[str] = []

    def fake_get(url: str) -> str:
        seen_urls.append(url)
        return _RSS

    items = collect_google_news(
        '"Hồ Tây" pháo hoa', window_days=7, http_get=fake_get, now=datetime(2026, 10, 1, tzinfo=timezone.utc)
    )

    assert [item["title"] for item in items] == ["Hà Nội dự kiến bắn 900 giàn pháo hoa tại hồ Tây tối 10/10"]
    assert items[0]["source_name"] == "VTV.vn"
    assert items[0]["id"] == headline_id(items[0]["title"])
    assert "when%3A7d" in seen_urls[0] and "hl=vi" in seen_urls[0]


def test_official_page_collector_dedupes_repeated_headlines_with_timestamps() -> None:
    page = """
    <a class="item-title" href="/van-hoa-xa-hoi/giai-pickleball-2026-1.htm"> Phường Tây Hồ tổ chức Giải Pickleball năm 2026 chào mừng </a>
    <a href="/van-hoa-xa-hoi/giai-pickleball-2026-1.htm">Phường Tây Hồ tổ chức Giải Pickleball năm 2026 chào mừng 21:00 19/10/2026</a>
    <a href="/an-ninh/abc.htm">Tin an ninh rất dài không thuộc mục văn hoá xã hội</a>
    """
    items = collect_official_page(
        "https://tayho.hanoi.gov.vn/van-hoa-xa-hoi", path_prefix="/van-hoa-xa-hoi/", source_name="Phường", http_get=lambda _: page
    )
    assert len(items) == 1
    assert items[0]["source_uri"] == "https://tayho.hanoi.gov.vn/van-hoa-xa-hoi/giai-pickleball-2026-1.htm"


def test_classifier_sends_today_and_normalises_event_fields() -> None:
    sent: list[dict] = []

    def client_fn(**kwargs) -> str:
        sent.append(json.loads(kwargs["contents"]))
        return json.dumps([
            {"id": "a", "geographic": "westlake", "thematic": "lifestyle_culture", "actionability": "direct",
             "type": "cultural_event", "brand_safety_category": "safe", "intersections": ["hanoi_westlake_local"],
             "is_event": True, "event_name": "Pháo hoa", "event_start": "2026-10-10", "event_end": None,
             "venue": "Hồ Tây", "westlake_area": True},
            {"id": "b", "geographic": "hanoi", "thematic": "unrelated", "actionability": "stretch",
             "type": "feature_story", "brand_safety_category": "safe", "intersections": [],
             "is_event": "yes", "event_start": "10/10/2026"},
        ])

    result = classify_candidates([{"id": "a", "title": "A"}, {"id": "b", "title": "B"}], api_key="k", client_fn=client_fn, today=_TODAY)

    assert sent[0]["today"] == "2026-10-01"
    by_id = {c["id"]: c for c in result}
    assert by_id["a"]["event_end"] == "2026-10-10"  # one-day event: end = start
    assert by_id["b"]["event_start"] is None and by_id["b"]["is_event"] is False


def test_classifier_drops_a_malformed_batch_without_losing_the_others() -> None:
    replies = iter(["not json", json.dumps([{"id": "x51", "geographic": "westlake"}])])
    candidates = [{"id": f"x{i}", "title": str(i)} for i in range(52)]
    result = classify_candidates(candidates, api_key="k", client_fn=lambda **_: next(replies), today=_TODAY)
    assert [c["id"] for c in result] == ["x51"]


def test_articles_about_one_event_collapse_into_one_candidate_with_sources() -> None:
    articles = [
        _event("a1", "Bắn 900 giàn pháo hoa trên hồ Tây dịp 10/10", "2026-10-10"),
        _event("a2", "Pháo hoa hồ Tây tối 10/10: vị trí xem đẹp", "2026-10-10"),
        _event("a3", "Giải đua thuyền rồng Hồ Tây", "2026-10-04", "2026-10-05"),
        {"id": "n1", "title": "Quán cà phê mới", "is_event": False},
    ]
    clusters = cluster_events(articles)

    events = [c for c in clusters if c.get("is_event")]
    assert len(events) == 2
    fireworks = next(c for c in events if c["event_start"] == "2026-10-10")
    assert fireworks["source_count"] == 2
    assert fireworks["id"].startswith("event-2026-10-10-")
    assert any(c["id"] == "n1" for c in clusters)


def test_same_event_needs_close_dates() -> None:
    assert not same_event(_event("a", "Lễ hội hoa sen Hồ Tây", "2026-06-01"), _event("b", "Lễ hội hoa sen Hồ Tây", "2026-07-01"))


def test_passed_events_are_rejected_and_upcoming_westlake_events_get_fast_lane() -> None:
    results = scan_trends(
        [
            _event("past", "Đua thuyền", "2026-09-20"),
            _event("soon", "Pháo hoa hồ Tây", "2026-10-10"),
            _event("far", "Lễ hội mùa xuân", "2026-12-20"),
            _event("tomorrow", "Chợ phiên", "2026-10-02"),
            _event("elsewhere", "Lễ hội Đà Lạt", "2026-10-10", westlake_area=False),
        ],
        _TREND_POLICY,
        _SAFETY_POLICY,
        today=_TODAY,
        fast_lane_policy={"min_days_ahead": 2, "max_days_ahead": 14},
    )
    by_id = {r["id"]: r for r in results}

    assert by_id["past"]["status"] == "rejected" and by_id["past"]["rejection_reason"] == "event_passed"
    # On the lake and on-brand even though the classifier called it "adjacent".
    assert by_id["soon"]["status"] == "needs_human_approval" and by_id["soon"]["geographic"] == "westlake"
    assert by_id["soon"]["fast_lane"] is True
    assert by_id["far"]["fast_lane"] is False  # beyond 14 days: normal queue
    assert by_id["tomorrow"]["fast_lane"] is False  # too close to draft + approve
    assert by_id["elsewhere"]["status"] == "rejected"  # hanoi 0.7 x 0.6 x 0.6 < 0.6
    assert results[0]["id"] == "soon"


def test_westlake_events_still_go_through_brand_safety() -> None:
    result = scan_trends([_event("bad", "Vụ việc", "2026-10-10", brand_safety_category="crime_scandal")], _TREND_POLICY, _SAFETY_POLICY, today=_TODAY)
    assert result[0]["status"] == "rejected" and result[0]["rejection_reason"] == "forbidden_trend_category"


def test_rescan_adds_sources_to_a_known_event_instead_of_re_proposing_it(tmp_path: Path) -> None:
    store = TrendCandidateStore(data_root=tmp_path)
    first = cluster_events([_event("a1", "Bắn pháo hoa trên hồ Tây dịp 10/10", "2026-10-10")])
    assert len(store.merge_new_detailed(first)) == 1
    store.reject(first[0]["id"], rejected_by="harry")

    tomorrow = cluster_events([_event("a9", "Pháo hoa hồ Tây tối 10/10 rực rỡ", "2026-10-10")])
    assert store.merge_new_detailed(tomorrow) == []

    rows = store.load()
    assert len(rows) == 1
    assert rows[0]["status"] == "rejected"  # Harry's no stands
    assert rows[0]["source_count"] == 2


def test_fetch_uses_configured_queries_pages_and_survives_a_failing_query() -> None:
    calls: list[str] = []

    def fake_collect(query: str, **kwargs) -> list[dict]:
        calls.append(query)
        if query == "broken":
            raise OSError("timeout")
        return [_event("a1", "Bắn pháo hoa trên hồ Tây", "2026-10-10"), _event("a2", "Pháo hoa hồ Tây 10/10", "2026-10-10")]

    def fake_page(url: str, **kwargs) -> list[dict]:
        return [_event("p1", "Chợ hoa Quảng An", "2026-10-12")]

    result = fetch_and_score_saturday_candidates(
        trend_policy=_TREND_POLICY,
        safety_policy=_SAFETY_POLICY,
        sources_config={
            "google_news": {"queries": ["broken", "q"]},
            "official_pages": [{"url": "https://p", "path_prefix": "/"}],
            "fast_lane": {"min_days_ahead": 2, "max_days_ahead": 14},
        },
        collect_fn=fake_collect,
        page_collect_fn=fake_page,
        classify_fn=lambda items: items,
        today=_TODAY,
    )

    assert calls == ["broken", "q"]
    assert len(result) == 2  # fireworks articles clustered + the flower market
    assert all(r["fast_lane"] for r in result)


def test_a_future_event_is_not_stale_because_its_headline_names_a_past_date() -> None:
    concert = _event("c", "Concert và bắn pháo hoa nhân Ngày Văn hóa (sau dịp 10/10/2026)", "2026-10-24")
    result = scan_trends([concert], _TREND_POLICY, _SAFETY_POLICY, today=date(2026, 10, 21))
    assert result[0]["status"] == "needs_human_approval"


def test_news_snippet_does_not_carry_the_byline_date() -> None:
    items = collect_google_news("q", http_get=lambda _: _RSS, now=datetime(2026, 10, 1, tzinfo=timezone.utc))
    assert "/" not in items[0]["snippet"]


def test_differently_named_reports_of_one_show_still_cluster() -> None:
    clusters = cluster_events([
        _event("f1", "Bắn 900 giàn pháo hoa trên mặt hồ Tây chào mừng Ngày Giải phóng Thủ đô", "2026-10-10"),
        _event("f2", "Bắn pháo hoa kết hợp âm nhạc tại Hồ Tây dịp 10/10", "2026-10-10"),
        _event("f3", "Trình diễn pháo hoa tại hồ Tây, hồ Hoàn Kiếm tối 10/10", "2026-10-10"),
        _event("x", "Hòa nhạc giao hưởng mùa thu", "2026-10-10"),
    ])
    assert sorted(c.get("source_count") for c in clusters) == [1, 3]


def test_trend_scan_cli_stores_only_proposals_and_reports_fast_lane(tmp_path: Path, monkeypatch) -> None:
    from typer.testing import CliRunner

    import research_engine.trend_radar.application.fetch_saturday_candidates as fetch_module
    import research_engine.trend_radar.trend_candidate_store as store_module
    from growth_orchestrator.cli import app

    scored = scan_trends(
        [_event("soon", "Pháo hoa hồ Tây", "2026-10-10"), _event("past", "Đua thuyền", "2026-09-20")],
        _TREND_POLICY, _SAFETY_POLICY, today=_TODAY, fast_lane_policy={"min_days_ahead": 2, "max_days_ahead": 14},
    )
    monkeypatch.setattr(fetch_module, "fetch_and_score_saturday_candidates", lambda **_: scored)
    original_init = store_module.TrendCandidateStore.__init__
    monkeypatch.setattr(
        store_module.TrendCandidateStore, "__init__", lambda self, project="venho_hotel", data_root=None: original_init(self, project, tmp_path)
    )
    monkeypatch.setenv("GEMINI_API_KEY", "fake")

    result = CliRunner().invoke(app, ["trend-scan"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["rejected_by_scan"] == 1 and payload["inserted_new"] == 1
    assert [e["id"] for e in payload["new_fast_lane"]] == ["soon"]
    assert [c["id"] for c in TrendCandidateStore(data_root=tmp_path).load()] == ["soon"]


def test_non_event_articles_about_one_story_collapse() -> None:
    def story(id_: str, title: str) -> dict:
        return {"id": id_, "title": title, "is_event": False, "source_uri": f"https://n/{id_}"}

    clusters = cluster_events([
        story("q1", "[ẢNH] Chợ hoa Quảng An nhộn nhịp, tấp nập trước dịp 20/10"),
        story("q2", "Không khí nhộn nhịp tại chợ hoa đêm lớn nhất Hà Nội dịp 20.10"),
        story("q3", "Du khách 'lạc bước' trong chợ hoa lớn nhất Hà Nội lúc rạng sáng"),
        story("b1", "Phong trào thuê xe đạp quanh Hồ Tây của giới trẻ"),
    ])
    assert sorted(c["source_count"] for c in clusters) == [1, 3]


def test_rescan_of_a_known_story_does_not_requeue_it(tmp_path: Path) -> None:
    store = TrendCandidateStore(data_root=tmp_path)
    store.merge_new_detailed([{"id": "q1", "title": "Chợ hoa Quảng An nhộn nhịp, tấp nập trước dịp 20/10", "is_event": False}])
    again = store.merge_new_detailed([{"id": "q9", "title": "Chợ hoa Quảng An nhộn nhịp về đêm", "is_event": False, "sources": [{"title": "Chợ hoa Quảng An nhộn nhịp về đêm"}]}])
    assert again == [] and len(store.load()) == 1
