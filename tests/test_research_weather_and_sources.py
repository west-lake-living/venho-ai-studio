"""Weather signals, named-URL sources, and the stale-event filter.

No network: every collector gets an injected transport.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from research_engine.application.extract_facts import dates_in, extract_fact_proposals, is_stale_dated
from research_engine.application.run_research_cycle import run_research_cycle
from research_engine.trend_radar.collectors.tavily_extract import MAX_CONTENT_CHARS, extract_urls
from research_engine.trend_radar.collectors.weather_api import (
    collect_weather_forecast,
    next_saturday,
    signal_for_date,
)
from shared.storage.weather_signal_store import WeatherSignalStore

ROOT = Path(__file__).resolve().parents[1]
REAL_CONFIG_ROOT = ROOT / "config/projects/venho_hotel/research"


def _forecast_payload(days: list[tuple[str, int, float, float]]) -> dict:
    return {
        "daily": {
            "time": [d[0] for d in days],
            "weathercode": [d[1] for d in days],
            "temperature_2m_max": [d[2] for d in days],
            "temperature_2m_min": [d[3] for d in days],
        }
    }


# --- weather conditions ----------------------------------------------------


@pytest.mark.parametrize(
    "code,tmax,tmin,expected",
    [
        (61, 30.0, 25.0, "rain"),          # rain rules out every outdoor scenario
        (45, 28.0, 22.0, "morning_mist"),  # the most valuable shot on the list
        (0, 28.0, 14.0, "cold_snap"),      # clear but genuinely cold for Hanoi
        (0, 35.0, 27.0, "heat"),
        (0, 30.0, 24.0, "clear_sunrise"),
        (3, 30.0, 24.0, "golden_sunset"),  # overcast: no sunrise, still a sunset
    ],
)
def test_forecast_maps_to_the_scenario_the_weather_actually_allows(code, tmax, tmin, expected) -> None:
    forecasts = collect_weather_forecast(
        lat=21.05, lon=105.82,
        http_get=lambda url, **kwargs: _forecast_payload([("2026-08-08", code, tmax, tmin)]),
        today=date(2026, 8, 6),
    )

    assert forecasts[0]["condition"] == expected
    assert forecasts[0]["visual_opportunity"]


def test_rain_beats_temperature_when_both_apply() -> None:
    """A rainy 35°C day is a rain day: the rooftop is unusable either way,
    but only one of those two produces a shootable image."""
    forecasts = collect_weather_forecast(
        lat=21.05, lon=105.82,
        http_get=lambda url, **kwargs: _forecast_payload([("2026-08-08", 80, 35.0, 27.0)]),
        today=date(2026, 8, 6),
    )

    assert forecasts[0]["condition"] == "rain"


def test_a_forecast_row_for_yesterday_is_dropped() -> None:
    """Timezone edges and cached provider responses would otherwise produce a
    signal that is already expired the moment it is written."""
    forecasts = collect_weather_forecast(
        lat=21.05, lon=105.82,
        http_get=lambda url, **kwargs: _forecast_payload(
            [("2026-08-05", 0, 30.0, 24.0), ("2026-08-06", 0, 30.0, 24.0)]
        ),
        today=date(2026, 8, 6),
    )

    assert [f["forecast_date"] for f in forecasts] == ["2026-08-06"]


def test_a_dead_weather_provider_returns_nothing_rather_than_raising() -> None:
    """Losing the forecast costs the Saturday post a hint. It must never cost
    the content run itself."""

    def boom(url, **kwargs):  # noqa: ANN001
        raise ConnectionError("open-meteo unreachable")

    assert collect_weather_forecast(lat=21.05, lon=105.82, http_get=boom) == []


# --- the weather cycle -----------------------------------------------------


def test_weather_cycle_writes_r2t_notes_and_never_proposes_a_fact(tmp_path: Path) -> None:
    """DoD #20: a weather signal shapes the angle and can never become a
    citable claim. There is deliberately no path from here to a fact."""
    vault = tmp_path / "vault"
    data_root = tmp_path / "data"

    result = run_research_cycle(
        "weather_signal",
        config_root=REAL_CONFIG_ROOT,
        vault_root=vault,
        data_root=data_root,
        today=date(2026, 8, 6),
        http_get=lambda url, **kwargs: _forecast_payload(
            [("2026-08-06", 45, 28.0, 22.0), ("2026-08-08", 0, 30.0, 24.0)]
        ),
    )

    assert result.ran
    assert result.proposals_created == 0
    notes = list((vault / "notes" / "weather_signal").glob("*.md"))
    assert len(notes) == 2
    body = notes[0].read_text(encoding="utf-8")
    assert "R2-T" in body

    signals = WeatherSignalStore(data_root=data_root).load()
    assert {s["forecast_date"] for s in signals} == {"2026-08-06", "2026-08-08"}
    assert all(s["fact_key"] is None for s in signals)


def test_the_store_hides_signals_whose_forecast_has_expired(tmp_path: Path) -> None:
    store = WeatherSignalStore(data_root=tmp_path)
    now = datetime(2026, 8, 8, 12, 0)
    store.replace(
        [
            {"rs_id": "fresh", "forecast_date": "2026-08-08", "expires_at": (now + timedelta(hours=6)).isoformat()},
            {"rs_id": "stale", "forecast_date": "2026-08-06", "expires_at": (now - timedelta(hours=1)).isoformat()},
        ]
    )

    assert [s["rs_id"] for s in store.valid_signals(now=now)] == ["fresh"]


def test_signal_lookup_targets_the_coming_saturday() -> None:
    assert next_saturday(date(2026, 8, 6)) == date(2026, 8, 8)   # Thursday -> Saturday
    assert next_saturday(date(2026, 8, 8)) == date(2026, 8, 8)   # already Saturday
    assert next_saturday(date(2026, 8, 9)) == date(2026, 8, 15)  # Sunday -> next week

    now = datetime(2026, 8, 6, 12, 0)
    signals = [
        {"forecast_date": "2026-08-08", "expires_at": (now + timedelta(hours=48)).isoformat(), "rs_id": "sat"},
        {"forecast_date": "2026-08-07", "expires_at": (now + timedelta(hours=48)).isoformat(), "rs_id": "fri"},
    ]

    assert signal_for_date(signals, date(2026, 8, 8), now=now)["rs_id"] == "sat"
    assert signal_for_date(signals, date(2026, 8, 15), now=now) is None


def test_an_expired_signal_is_never_handed_to_a_content_package() -> None:
    """preflight would fail the dispatch on it (`weather_signal_expired`) --
    correct, but needlessly late."""
    now = datetime(2026, 8, 8, 12, 0)
    signals = [{"forecast_date": "2026-08-08", "expires_at": (now - timedelta(hours=1)).isoformat(), "rs_id": "sat"}]

    assert signal_for_date(signals, date(2026, 8, 8), now=now) is None


# --- the Saturday brief ----------------------------------------------------


def test_saturday_brief_carries_weather_as_context_not_as_a_proof_point() -> None:
    from agent_studio.growth.scenario_registry import ScenarioRegistry
    from growth_orchestrator.application.daily_cycle import _build_creative_brief

    topic = {
        "dna_subject": "outside",
        "topic": "Một buổi chiều ở sảnh",
        "pillar": "Feature story",
        "weather_context": {
            "rs_id": "RS-weather-2026-08-08",
            "condition": "rain",
            "visual_opportunity": "Mưa ngoài cửa kính — không gian ấm trong sảnh",
            "matching_scenario_keys": ["venho_lobby_cozy"],
            "expires_at": "2026-08-08T21:00:00",
        },
    }

    brief = _build_creative_brief(topic, "facebook", "saturday", "venho_hotel", ScenarioRegistry.from_file())

    assert brief["context_refs"] == [
        {"rs_id": "RS-weather-2026-08-08", "evidence_level": "R2-T", "role": "weather_angle"}
    ]
    assert brief["proof_points"] == []  # a forecast is never a claim
    assert brief["hook_hypothesis"] == "Mưa ngoài cửa kính — không gian ấm trong sảnh"


def test_rain_moves_the_saturday_shoot_indoors() -> None:
    """The point of the whole weather path: a rooftop brief on a rainy
    weekend produces an image the weather contradicts."""
    from agent_studio.growth.scenario_registry import ScenarioRegistry
    from growth_orchestrator.application.daily_cycle import _build_creative_brief

    topic = {
        "dna_subject": "outside",  # normally venho_rooftop_sunrise
        "topic": "Cuối tuần ở Ven Ho",
        "pillar": "Feature story",
        "weather_context": {
            "rs_id": "RS-weather-2026-08-08",
            "condition": "rain",
            "visual_opportunity": "Mưa ngoài cửa kính",
            "matching_scenario_keys": ["venho_lobby_cozy"],
        },
    }

    brief = _build_creative_brief(topic, "facebook", "saturday", "venho_hotel", ScenarioRegistry.from_file())

    assert brief["visual"]["scenario_key"] == "venho_lobby_cozy"


def test_every_scenario_the_weather_policy_maps_to_actually_exists() -> None:
    """weather_policy.yaml referenced three scenario keys that were never in
    the registry, so four of the six conditions -- rain included -- could not
    influence a brief at all."""
    from agent_studio.growth.scenario_registry import ScenarioRegistry

    policy = yaml.safe_load((REAL_CONFIG_ROOT / "weather_policy.yaml").read_text(encoding="utf-8"))
    registry = ScenarioRegistry.from_file()

    for condition, keys in policy["scenario_mapping"].items():
        for key in keys:
            assert key in registry.scenarios, f"{condition} maps to unknown scenario {key}"


def test_an_unknown_weather_scenario_leaves_the_topics_own_visual_alone() -> None:
    from agent_studio.growth.scenario_registry import ScenarioRegistry
    from growth_orchestrator.application.daily_cycle import _build_creative_brief

    brief = _build_creative_brief(
        {
            "dna_subject": "outside",
            "topic": "T",
            "pillar": "P",
            "weather_context": {"rs_id": "w", "matching_scenario_keys": ["venho_not_a_real_scenario"]},
        },
        "facebook", "saturday", "venho_hotel", ScenarioRegistry.from_file(),
    )

    assert brief["visual"]["scenario_key"] == "venho_rooftop_sunrise"


def test_a_brief_without_weather_is_unchanged() -> None:
    from agent_studio.growth.scenario_registry import ScenarioRegistry
    from growth_orchestrator.application.daily_cycle import _build_creative_brief

    brief = _build_creative_brief(
        {"dna_subject": "outside", "topic": "T", "pillar": "P"},
        "facebook", "saturday", "venho_hotel", ScenarioRegistry.from_file(),
    )

    assert "context_refs" not in brief


# --- stale events ----------------------------------------------------------


def test_dates_are_read_out_of_vietnamese_event_values() -> None:
    assert dates_in("09/11/2024 - 17/11/2024") == [date(2024, 11, 9), date(2024, 11, 17)]
    assert dates_in("2026-06-26") == [date(2026, 6, 26)]
    assert dates_in("31/02/2026") == []  # not a real date
    assert dates_in("Tháng 10 đến tháng 2") == []


def test_dates_written_without_a_year_are_read_against_today() -> None:
    """The forms Vietnamese listings actually use. Every one of these was
    invisible until 2026-08-07, which is why the Lotus Festival sat in the
    Trend Radar six weeks after it ended."""
    today = date(2026, 8, 7)

    # The exact title Harry was looking at.
    assert dates_in("Lễ hội Sen Hà Nội diễn ra từ ngày 26-28/6", today=today) == [
        date(2026, 6, 26), date(2026, 6, 28),
    ]
    # Nearest June, not next June.
    assert dates_in("từ 26-28/6", today=date(2026, 5, 1)) == [date(2026, 6, 26), date(2026, 6, 28)]
    assert dates_in("ngày 15/8", today=today) == [date(2026, 8, 15)]
    # Vietnamese month names, the Sputnik index page's format.
    assert dates_in("5 Tháng Ba 2024, 08:49", today=today) == [date(2024, 3, 5)]
    assert dates_in("17 Tháng Mười Một 2021", today=today) == [date(2021, 11, 17)]
    assert dates_in("ngày 15 tháng 8 năm 2024", today=today) == [date(2024, 8, 15)]
    # Without `today` a yearless date is skipped rather than guessed at.
    assert dates_in("từ ngày 26-28/6") == []


def test_a_rating_is_not_read_as_a_date() -> None:
    """"8/10" is why the bare dd/mm form requires an explicit "ngày" cue --
    guest_voice snippets are full of scores, and each one would otherwise
    date-stamp its candidate to October."""
    today = date(2026, 8, 7)
    assert dates_in("Agoda 8.5/10, vị trí 9/10", today=today) == []
    assert is_stale_dated("Điểm sạch sẽ 8/10", today=today) is False
    # A real year is still not swallowed by the range form either way round.
    assert dates_in("09/11/2024 - 17/11/2024", today=today) == [date(2024, 11, 9), date(2024, 11, 17)]


def test_a_bare_month_is_still_a_season_not_a_date() -> None:
    """The seasonal-answer guarantee has to survive the new patterns: a
    `local_events` value of "Tháng 10 đến tháng 2" is an answer about when to
    visit, and marking it expired would delete a correct fact."""
    today = date(2026, 8, 7)
    assert dates_in("Tháng 10 đến tháng 2", today=today) == []
    assert is_stale_dated("Tháng 10 đến tháng 2", today=today) is False
    assert is_stale_dated("mùa sen tháng 6", today=today) is False


def test_an_event_that_already_ended_is_stale_and_a_seasonal_answer_is_not() -> None:
    today = date(2026, 8, 6)

    # The two the first real cycle actually proposed.
    assert is_stale_dated("09/11/2024 - 17/11/2024", today=today) is True
    assert is_stale_dated("19/09/2024 - 22/09/2024", today=today) is True
    # A range that has started but not finished is live.
    assert is_stale_dated("01/08/2026 - 30/08/2026", today=today) is False
    # No date at all is an answer, not an expiry.
    assert is_stale_dated("Tháng 10 đến tháng 2", today=today) is False


def test_the_extractor_drops_a_past_event_the_model_proposed_anyway() -> None:
    """Belt and braces: the prompt is told today's date, and this catches
    what the instruction misses."""
    response = json.dumps(
        [
            {"fact_key": "event.old_festival", "value": "09/11/2024 - 17/11/2024", "value_type": "string", "source_index": 0},
            {"fact_key": "event.upcoming", "value": "20/09/2026", "value_type": "string", "source_index": 0},
        ],
        ensure_ascii=False,
    )

    proposals = extract_fact_proposals(
        question="Sự kiện nào sắp diễn ra?",
        sources=[{"title": "A", "source_uri": "https://example.com/a", "snippet": "..."}],
        api_key="fake",
        client_fn=lambda **kwargs: response,
        today=date(2026, 8, 6),
    )

    assert [p["fact_key"] for p in proposals] == ["event.upcoming"]


def test_todays_date_reaches_the_prompt() -> None:
    captured = {}

    def client_fn(*, model, system, contents):  # noqa: ANN001
        captured["system"] = system
        return "[]"

    extract_fact_proposals(
        question="Q", sources=[{"title": "A", "source_uri": "u", "snippet": "s"}],
        api_key="fake", client_fn=client_fn, today=date(2026, 8, 6),
    )

    assert "2026-08-06" in captured["system"]


def test_staleness_filtering_can_be_turned_off_per_domain() -> None:
    """market_pricing legitimately answers with past reference years."""
    response = json.dumps(
        [{"fact_key": "market.record_year", "value": "01/01/2019", "value_type": "string", "source_index": 0}],
        ensure_ascii=False,
    )

    proposals = extract_fact_proposals(
        question="Q", sources=[{"title": "A", "source_uri": "u", "snippet": "s"}],
        api_key="fake", client_fn=lambda **kwargs: response,
        today=date(2026, 8, 6), reject_past_dates=False,
    )

    assert len(proposals) == 1


# --- named URLs ------------------------------------------------------------


def test_extract_reads_the_exact_pages_it_was_given() -> None:
    def http_post(url, *, json=None, headers=None, timeout=None):  # noqa: ANN001, A002
        assert json["urls"] == ["https://www.agoda.com/ven-ho-hotel/reviews"]
        return {
            "results": [
                {
                    "url": "https://www.agoda.com/ven-ho-hotel/reviews",
                    "title": "Ven Ho Hotel Reviews",
                    "raw_content": "Phòng sạch, nhân viên thân thiện. Thang máy chậm.",
                }
            ]
        }

    sources = extract_urls(["https://www.agoda.com/ven-ho-hotel/reviews"], api_key="fake", http_post=http_post)

    assert len(sources) == 1
    assert "Thang máy chậm" in sources[0]["snippet"]
    assert sources[0]["source_uri"] == "https://www.agoda.com/ven-ho-hotel/reviews"


def test_pages_that_fail_to_extract_are_absent_not_fatal() -> None:
    """Partial results are the norm: a paywalled or JS-only page should not
    lose the ones that worked."""

    def http_post(url, **kwargs):  # noqa: ANN001
        return {"results": [{"url": "https://a.com", "raw_content": "ok"}, {"url": "https://b.com", "raw_content": ""}]}

    sources = extract_urls(["https://a.com", "https://b.com"], api_key="fake", http_post=http_post)

    assert [s["source_uri"] for s in sources] == ["https://a.com"]


def test_a_long_page_is_capped_before_it_reaches_the_prompt() -> None:
    def http_post(url, **kwargs):  # noqa: ANN001
        return {"results": [{"url": "https://a.com", "raw_content": "x" * 50_000}]}

    sources = extract_urls(["https://a.com"], api_key="fake", http_post=http_post)

    assert len(sources[0]["snippet"]) == MAX_CONTENT_CHARS


def test_link_and_image_markup_is_stripped_before_the_cap_applies() -> None:
    """The bug that made the first real guest_voice run return 0 proposals.

    An OTA listing is mostly markdown link syntax; head-truncating the raw
    form kept the nav bar and cut off before any guest review.
    """
    noise = "".join(f"[nav {i}](https://booking.com/x?aid={i}&sid=abc)\n" for i in range(200))
    body = "Khách khen nhân viên thân thiện."

    def http_post(url, **kwargs):  # noqa: ANN001
        return {"results": [{"url": "https://a.com", "raw_content": noise + body}]}

    snippet = extract_urls(["https://a.com"], api_key="fake", http_post=http_post)[0]["snippet"]

    assert "https://" not in snippet
    assert body in snippet


def test_named_urls_take_priority_and_merge_with_the_domains_search(tmp_path: Path) -> None:
    config_root = tmp_path / "config"
    config_root.mkdir()
    (config_root / "research_questions.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "domains": {
                    "competitor": {
                        "question": "Giá phòng quanh Hồ Tây ở mức nào?",
                        "collector": "tavily",
                        "queries": ["q"],
                        "urls": ["https://www.booking.com/rival"],
                    }
                },
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    def http_post(url, *, json=None, headers=None, timeout=None):  # noqa: ANN001, A002
        if "extract" in url:
            return {"results": [{"url": "https://www.booking.com/rival", "title": "Rival", "raw_content": "1.000.000đ"}]}
        return {"results": [{"url": "https://search-result.com", "title": "S", "content": "800.000đ", "score": 0.5}]}

    result = run_research_cycle(
        "competitor", config_root=config_root, vault_root=tmp_path / "vault", data_root=tmp_path / "data",
        tavily_api_key="fake", gemini_api_key="", http_post=http_post,
        extract_fn=lambda **kwargs: [], today=date(2026, 8, 6),
    )

    assert result.sources_collected == 2
    assert "Rival" in result.source_notes[0]  # the named page leads


def test_a_url_domain_runs_without_needing_an_export_file(tmp_path: Path) -> None:
    """guest_voice becomes automatic the moment Harry fills in `urls`."""
    config_root = tmp_path / "config"
    config_root.mkdir()
    (config_root / "research_questions.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "domains": {
                    "guest_voice": {
                        "question": "Khách khen chê gì?",
                        "collector": "manual",
                        "urls": ["https://www.agoda.com/ven-ho-hotel/reviews"],
                    }
                },
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    result = run_research_cycle(
        "guest_voice", config_root=config_root, vault_root=tmp_path / "vault", data_root=tmp_path / "data",
        tavily_api_key="fake", gemini_api_key="",
        http_post=lambda url, **kwargs: {"results": [{"url": "https://www.agoda.com/ven-ho-hotel/reviews", "raw_content": "Phòng sạch"}]},
        extract_fn=lambda **kwargs: [], today=date(2026, 8, 6),
    )

    assert result.ran
    assert result.sources_collected == 1
