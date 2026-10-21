from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import growth_orchestrator.application.topic_ideation as ideation
from growth_orchestrator.application.daily_cycle import _pick_regular_topic, _trend_topic_text
from growth_orchestrator.application.topic_ideation import ideate_topics, ideation_enabled, too_similar

_LANE = {"id": "west_lake_life", "name": "Ho Tay dau tuan", "topics": ["suong som tren mat ho", "nguoi tap the duc quanh ho"]}
_CALENDAR = {"months": {10: ["hoa sữa", "cốm làng Vòng"]}, "hotel_angles": ["rooftop nhìn ra hồ"]}


def test_ideation_is_off_unless_explicitly_enabled(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.delenv("GROWTH_TOPIC_IDEATION", raising=False)
    assert ideation_enabled() is False
    monkeypatch.setenv("GROWTH_TOPIC_IDEATION", "1")
    assert ideation_enabled() is True


def test_similarity_ignores_words_every_topic_shares() -> None:
    assert too_similar("Một vòng xe đạp quanh Hồ Tây đầu tuần", "mot vong xe quanh ho de bat dau tuan moi")
    assert not too_similar("Mùa hoa sữa trên đường Thanh Niên", "Hoàng hôn rooftop Ven Hồ Hotel")


def test_ideas_too_close_to_recent_posts_or_each_other_are_dropped() -> None:
    sent: list[dict] = []

    def client_fn(**kwargs) -> str:
        sent.append(json.loads(kwargs["contents"]))
        return json.dumps([
            "Mùa hoa sữa thơm nồng trên đường Thanh Niên buổi tối",
            "Một vòng xe đạp quanh Hồ Tây đầu tuần mới",  # repeat of a posted topic
            "Hoa sữa thơm nồng đường Thanh Niên lúc tối muộn",  # repeat of idea 1
            "Cốm làng Vòng gói lá sen, ăn bên mép hồ sáng sớm",
            "ngắn",
            42,
        ])

    ideas = ideate_topics(
        _LANE, target_date=date(2026, 10, 26), calendar=_CALENDAR,
        recent_topics=["mot vong xe quanh ho de bat dau tuan moi"], client_fn=client_fn,
    )

    assert ideas == [
        "Mùa hoa sữa thơm nồng trên đường Thanh Niên buổi tối",
        "Cốm làng Vòng gói lá sen, ăn bên mép hồ sáng sớm",
    ]
    assert sent[0]["seasonal_hooks_this_month"] == ["hoa sữa", "cốm làng Vòng"]
    assert "mot vong xe quanh ho de bat dau tuan moi" in sent[0]["already_posted"]


def test_ideation_failure_returns_nothing() -> None:
    def boom(**_):
        raise RuntimeError("quota")

    assert ideate_topics(_LANE, target_date=date(2026, 10, 26), calendar=_CALENDAR, recent_topics=[], client_fn=boom) == []


def test_regular_lane_prefers_ideas_over_curated_when_enabled(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GROWTH_TOPIC_IDEATION", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setattr(ideation, "ideate_topics", lambda *a, **k: ["Mùa hoa sữa trên đường Thanh Niên buổi tối"])

    picked = _pick_regular_topic(_LANE, "monday", "venho_hotel", tmp_path)

    assert picked["topic"] == "Mùa hoa sữa trên đường Thanh Niên buổi tối"
    assert picked["topic_source"] == "ideation"


def test_regular_lane_falls_back_to_curated_without_ideation(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("GROWTH_TOPIC_IDEATION", raising=False)
    picked = _pick_regular_topic(_LANE, "monday", "venho_hotel", tmp_path)
    assert picked["topic"] in _LANE["topics"]


def test_trend_topic_is_the_event_name_or_a_cleaned_headline() -> None:
    assert _trend_topic_text({"event_name": "Bắn pháo hoa trên Hồ Tây", "title": "x"}) == "Bắn pháo hoa trên Hồ Tây"
    assert _trend_topic_text({"title": "TOP 10 Quán cafe Hồ Tây view đẹp"}) == "Quán cafe Hồ Tây view đẹp"
    assert _trend_topic_text({"title": "Sen Tây Hồ: Tinh hoa văn hoá Việt | Văn hoá và sự kiện"}) == "Sen Tây Hồ: Tinh hoa văn hoá Việt"
