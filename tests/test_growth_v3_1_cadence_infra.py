from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from growth_orchestrator.application.manage_queue import runway_status
from growth_orchestrator.application.manage_slots import generate_slots
from growth_orchestrator.application.preflight import run_preflight_check
from growth_orchestrator.application.special_lane import select_special_lane_candidate, special_lane_timeline_state
from growth_orchestrator.domain.publishing_slot import PublishingSlot
from publishing_gateway.adapters.zalo_oa import ZaloOAAdapter
from research_engine.trend_radar.application.scan_weather import scan_weather
from research_engine.trend_radar.domain.weather_signal import WeatherSignal
from shared.notify.telegram import MockTelegramNotifier, send_alert

ROOT = Path(__file__).resolve().parents[1]
CADENCE_POLICY = yaml.safe_load((ROOT / "config/projects/venho_hotel/growth/cadence_policy.yaml").read_text(encoding="utf-8"))
QUEUE_POLICY = yaml.safe_load((ROOT / "config/projects/venho_hotel/growth/queue_policy.yaml").read_text(encoding="utf-8"))
WEATHER_POLICY = yaml.safe_load((ROOT / "config/projects/venho_hotel/research/weather_policy.yaml").read_text(encoding="utf-8"))


# --- cadence + slots (PB-001) --------------------------------------------


def test_cadence_policy_is_fixed_4_slots_no_ramp() -> None:
    assert CADENCE_POLICY["version"] == 2
    assert "stages" not in CADENCE_POLICY
    days = {slot["day"] for slot in CADENCE_POLICY["slots"]}
    assert days == {"monday", "wednesday", "friday", "saturday"}
    saturday = next(slot for slot in CADENCE_POLICY["slots"] if slot["day"] == "saturday")
    assert saturday["type"] == "special"


def test_generate_slots_produces_4_slots_per_week_over_horizon() -> None:
    # 2026-08-03 is a Monday.
    slots = generate_slots(CADENCE_POLICY, start_date=date(2026, 8, 3), horizon_days=14)
    assert len(slots) == 8  # two full weeks x 4 slots/week
    assert all(isinstance(slot, PublishingSlot) for slot in slots)
    assert all(slot.status == "OPEN" for slot in slots)
    regular = [slot for slot in slots if slot.slot_type == "regular"]
    special = [slot for slot in slots if slot.slot_type == "special"]
    assert len(regular) == 6
    assert len(special) == 2


def test_generate_slots_is_deterministic_and_idempotent() -> None:
    first = generate_slots(CADENCE_POLICY, start_date=date(2026, 8, 3), horizon_days=7)
    second = generate_slots(CADENCE_POLICY, start_date=date(2026, 8, 3), horizon_days=7)
    assert [slot.slot_id for slot in first] == [slot.slot_id for slot in second]


# --- PublishingSlot state machine (§4.4) ---------------------------------


def test_publishing_slot_happy_path_transitions() -> None:
    slot = PublishingSlot(slot_id="s1", slot_date="2026-08-03", slot_type="regular", lane="regular")
    slot = slot.transition("DRAFT_ASSIGNED")
    slot = slot.transition("PENDING_APPROVAL")
    slot = slot.transition("FILLED", content_package_id="pkg-1", filled_from="pipeline")
    slot = slot.transition("DISPATCHED")
    slot = slot.transition("COMPLETED")
    assert slot.status == "COMPLETED"
    assert slot.content_package_id == "pkg-1"


def test_publishing_slot_evergreen_fallback_path() -> None:
    # As of 2026-08-06, evergreen fallback still lands in PENDING_APPROVAL
    # (Harry's decision: one Duyệt click required, no auto-dispatch even for
    # a previously-approved post -- see PublishingSlot.transition's docstring
    # and DoD #23) rather than jumping straight to DISPATCHED.
    slot = PublishingSlot(slot_id="s2", slot_date="2026-08-08", slot_type="special", lane="special")
    slot = slot.transition("DRAFT_ASSIGNED")
    slot = slot.transition("EVERGREEN_FALLBACK", filled_from="evergreen")
    slot = slot.transition("PENDING_APPROVAL")
    slot = slot.transition("FILLED", content_package_id="pkg-evergreen-1", filled_from="evergreen")
    slot = slot.transition("DISPATCHED")
    assert slot.status == "DISPATCHED"
    assert slot.filled_from == "evergreen"


def test_publishing_slot_rejects_forbidden_transition() -> None:
    slot = PublishingSlot(slot_id="s3", slot_date="2026-08-03", slot_type="regular", lane="regular")
    with pytest.raises(ValueError, match="Invalid PublishingSlot transition"):
        slot.transition("DISPATCHED")


def test_publishing_slot_draft_assigned_can_go_missed_when_generation_totally_fails() -> None:
    slot = PublishingSlot(slot_id="s4", slot_date="2026-08-10", slot_type="regular", lane="regular")
    slot = slot.transition("DRAFT_ASSIGNED")
    slot = slot.transition("MISSED")
    assert slot.status == "MISSED"


def test_publishing_slot_missed_requires_evergreen_exhausted() -> None:
    slot = PublishingSlot(slot_id="s4", slot_date="2026-08-03", slot_type="regular", lane="regular")
    with pytest.raises(ValueError, match="evergreen pool"):
        slot.assert_missed_only_after_evergreen_exhausted(evergreen_exhausted=False)
    slot.assert_missed_only_after_evergreen_exhausted(evergreen_exhausted=True)  # does not raise


def test_publishing_slot_missed_requires_evergreen_exhausted_from_draft_assigned_too() -> None:
    # Before 2026-08-06 this guard only checked status == "OPEN", which never
    # fired for the real daily_cycle failure path (DRAFT_ASSIGNED) -- dead
    # code in production despite a passing unit test. See publishing_slot.py.
    slot = PublishingSlot(slot_id="s5", slot_date="2026-08-03", slot_type="regular", lane="regular")
    slot = slot.transition("DRAFT_ASSIGNED")
    with pytest.raises(ValueError, match="evergreen pool"):
        slot.assert_missed_only_after_evergreen_exhausted(evergreen_exhausted=False)
    slot.assert_missed_only_after_evergreen_exhausted(evergreen_exhausted=True)  # does not raise


def test_publishing_slot_evergreen_fallback_requires_draft_assigned_first() -> None:
    # OPEN -> EVERGREEN_FALLBACK directly is still allowed (kept for the
    # domain model's completeness/future callers) but the real daily_cycle
    # path always goes through DRAFT_ASSIGNED first -- both are exercised so
    # neither silently breaks.
    slot = PublishingSlot(slot_id="s6", slot_date="2026-08-03", slot_type="regular", lane="regular")
    slot = slot.transition("EVERGREEN_FALLBACK", filled_from="evergreen")
    assert slot.status == "EVERGREEN_FALLBACK"


# --- runway policy, slot-based (§9.2 / PB-003) ---------------------------


@pytest.mark.parametrize(
    "open_slots,expected",
    [(6, "healthy"), (5, "warning"), (4, "warning"), (3, "critical"), (2, "critical"), (1, "empty"), (0, "empty")],
)
def test_runway_status_uses_slot_thresholds(open_slots: int, expected: str) -> None:
    assert runway_status(open_slots, QUEUE_POLICY) == expected


def test_check_runway_counts_open_slots_in_horizon_and_reports_status() -> None:
    from growth_orchestrator.application.manage_queue import check_runway

    tmp_db = Path("/tmp") / f"check_runway_test_{id(object())}.db"
    try:
        from shared.jobs.slot_store import SlotStore

        store = SlotStore(db_path=tmp_db)
        today = date.today()
        # 3 OPEN slots inside the default 14-day horizon -> "critical" per QUEUE_POLICY thresholds.
        for offset in range(3):
            slot_date = (today + timedelta(days=offset)).isoformat()
            store.ensure_slots([PublishingSlot(slot_id=f"slot-{slot_date}-x", slot_date=slot_date, slot_type="regular", lane="regular")])

        result = check_runway(project="venho_hotel", slot_store=store, chat_id=None)

        assert result["open_slot_count"] == 3
        assert result["status"] == "critical"
        assert "alert" not in result  # no chat_id resolved -> no alert attempt
    finally:
        tmp_db.unlink(missing_ok=True)


def test_check_runway_sends_telegram_alert_when_critical() -> None:
    from growth_orchestrator.application.manage_queue import check_runway
    from shared.notify.telegram import MockTelegramNotifier

    tmp_db = Path("/tmp") / f"check_runway_alert_test_{id(object())}.db"
    try:
        from shared.jobs.slot_store import SlotStore

        store = SlotStore(db_path=tmp_db)
        today = date.today()
        slot_date = today.isoformat()
        store.ensure_slots([PublishingSlot(slot_id=f"slot-{slot_date}-x", slot_date=slot_date, slot_type="regular", lane="regular")])

        notifier = MockTelegramNotifier()
        result = check_runway(project="venho_hotel", slot_store=store, notifier=notifier, chat_id="123456")

        assert result["status"] == "empty"
        assert len(notifier.sent) == 1
        assert notifier.sent[0]["chat_id"] == "123456"
        assert "empty" in notifier.sent[0]["text"].lower()
    finally:
        tmp_db.unlink(missing_ok=True)


# --- special lane T3->T7 (§9.5 / PB-008) ---------------------------------


def test_special_lane_prefers_higher_priority_type_over_lower() -> None:
    candidates = [
        {"type": "feature_story", "id": "c-fallback"},
        {"type": "lifestyle_trend", "id": "c-lifestyle"},
    ]
    chosen = select_special_lane_candidate(candidates)
    assert chosen["id"] == "c-lifestyle"
    assert chosen["selected_reason"] == "lifestyle_trend"


def test_special_lane_skips_unverified_cultural_event() -> None:
    candidates = [
        {"type": "cultural_event", "id": "c-event", "verified_by_human": False},
        {"type": "feature_story", "id": "c-fallback"},
    ]
    chosen = select_special_lane_candidate(candidates)
    assert chosen["id"] == "c-fallback"


def test_special_lane_falls_back_to_feature_story_when_nothing_else_qualifies() -> None:
    chosen = select_special_lane_candidate([{"type": "feature_story", "id": "only-fallback"}])
    assert chosen["id"] == "only-fallback"


def test_special_lane_raises_without_mandatory_fallback() -> None:
    with pytest.raises(ValueError, match="feature_story"):
        select_special_lane_candidate([])


def test_special_lane_timeline_hard_cutoff_falls_back_to_evergreen() -> None:
    assert special_lane_timeline_state(day="friday_after_cutoff", digest_ready=True, approved=False) == "fallback_evergreen"
    assert special_lane_timeline_state(day="friday_before_cutoff", digest_ready=True, approved=False) == "awaiting_approval"
    assert special_lane_timeline_state(day="saturday", digest_ready=True, approved=True) == "dispatched"


# --- pre-flight check (§9.4 / PB-005) -------------------------------------


def test_preflight_passes_clean_package() -> None:
    now = datetime(2026, 8, 3, 8, 45, tzinfo=timezone.utc)
    package = {
        "referenced_facts": [{"fact_key": "hotel.room_count", "valid_to": None}],
        "approval_status": "approved",
        "assets": [{"asset_id": "a1", "reachable": True, "hash": "abc", "expected_hash": "abc"}],
        "event_claims": [],
    }
    result = run_preflight_check(package, now=now)
    assert result == {"passed": True, "failures": []}


def test_preflight_catches_expired_fact_and_revoked_approval_and_bad_asset() -> None:
    now = datetime(2026, 8, 3, 8, 45, tzinfo=timezone.utc)
    package = {
        "referenced_facts": [{"fact_key": "hotel.promo", "valid_to": "2026-08-01T00:00:00+00:00"}],
        "approval_status": "revoked",
        "assets": [{"asset_id": "a1", "reachable": False, "hash": "abc", "expected_hash": "abc"}],
        "event_claims": [{"rs_id": "RS-1", "verified_by_human": False}],
        "weather_context": {"rs_id": "RS-weather-1", "expires_at": "2026-08-02T00:00:00+00:00"},
    }
    result = run_preflight_check(package, now=now)
    assert result["passed"] is False
    assert "fact_expired:hotel.promo" in result["failures"]
    assert "approval_not_valid:revoked" in result["failures"]
    assert "asset_unreachable_or_hash_mismatch:a1" in result["failures"]
    assert "event_not_verified:RS-1" in result["failures"]
    assert "weather_signal_expired:RS-weather-1" in result["failures"]


# --- weather signal is R2-T only, never a claim (§5.5 / §6.6) -----------


def test_weather_signal_never_carries_a_fact_key() -> None:
    signal = WeatherSignal(
        rs_id="RS-2026-08-0044",
        forecast_date="2026-08-06",
        condition="morning_mist",
        expires_at="2026-08-07T00:00:00+07:00",
    )
    assert signal.fact_key is None
    with pytest.raises(Exception):
        WeatherSignal(
            rs_id="RS-2026-08-0044",
            forecast_date="2026-08-06",
            condition="morning_mist",
            expires_at="2026-08-07T00:00:00+07:00",
            fact_key="hotel.weather_today",
        )


def test_scan_weather_expiry_is_policy_driven_not_provider_supplied() -> None:
    generated_at = datetime(2026, 8, 5, 6, 0, tzinfo=timezone.utc)
    forecasts = [{"forecast_date": "2026-08-06", "condition": "morning_mist", "temperature_range": [24, 31]}]
    signals = scan_weather(forecasts, policy=WEATHER_POLICY, generated_at=generated_at)
    assert len(signals) == 1
    signal = signals[0]
    expected_expiry = generated_at + timedelta(hours=WEATHER_POLICY["expiry_hours"])
    assert signal.expires_at == expected_expiry.isoformat()
    assert "venho_lake_view_room_sunrise" in signal.matching_scenario_keys


# --- Telegram alerts (shared, IN-D4) --------------------------------------


def test_send_alert_routes_through_mock_notifier_by_default() -> None:
    notifier = MockTelegramNotifier()
    policy = {"events": {"runway_empty": {"channel": "telegram", "severity": "critical"}}}
    result = send_alert("runway_empty", "Slot T2 chua co bai", notifier=notifier, chat_id="harry", policy=policy)
    assert result["severity"] == "critical"
    assert notifier.sent == [{"chat_id": "harry", "text": "[CRITICAL] Slot T2 chua co bai"}]


def test_send_alert_rejects_unknown_event() -> None:
    notifier = MockTelegramNotifier()
    with pytest.raises(ValueError, match="Unknown alert event"):
        send_alert("not_a_real_event", "x", notifier=notifier, chat_id="harry", policy={"events": {}})


# --- Zalo adapter, flag off by default (IN-D5) ---------------------------


def test_zalo_adapter_disabled_by_default() -> None:
    adapter = ZaloOAAdapter()
    result = adapter.send({"publication_id": "pub-1"})
    assert result["status"] == "DISABLED"
    assert result["published"] is False


def test_zalo_adapter_accepted_when_enabled() -> None:
    adapter = ZaloOAAdapter(enabled=True)
    result = adapter.send({"publication_id": "pub-1"})
    assert result["status"] == "GATEWAY_ACCEPTED"
    assert result["published"] is False

# NOTE (2026-08-05): tests for infra/heartbeat.py and infra/cloud_fallback/
# (Mac Mini deadman switch + HMAC-signed cloud fallback export) removed here
# along with the module itself -- that design was superseded by the real
# GitHub Actions + git-sync architecture documented in Phần 10 of
# VENHO_GROWTH_AGENT_MASTER_PLAN_v3_1_CONSOLIDATED.md. Neither module had any
# caller outside this test file.
