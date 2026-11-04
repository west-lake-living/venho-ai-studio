from __future__ import annotations

from datetime import date

from growth_engine.domain.channels.channel import (
    Channel,
    ChannelConfig,
    ChannelPlatform,
    config_hash,
)
from growth_engine.domain.kernel.time import BusinessCalendar
from growth_engine.domain.scheduling.cadence import CadencePolicy, CadenceRule, plan_slots


# Lịch dưới đây được dựng từ cadence v2 hiện có; dữ liệu test synthetic, cần thay bằng fixture thật từ P0-T03/P0-T04.
POLICY = CadencePolicy(
    version=2,
    project_id="venho_hotel",
    timezone="Asia/Ho_Chi_Minh",
    publish_time="09:00",
    rules=(
        CadenceRule(weekday=0, slot_type="regular", lane="regular"),
        CadenceRule(weekday=2, slot_type="regular", lane="regular"),
        CadenceRule(weekday=4, slot_type="regular", lane="regular"),
        CadenceRule(weekday=5, slot_type="special", lane="special"),
    ),
)


def test_fourteen_day_horizon_from_november_fifth_has_eight_slots() -> None:
    calendar = BusinessCalendar("Asia/Ho_Chi_Minh")
    slots = plan_slots(POLICY, date(2026, 11, 5), 14, calendar)
    assert len(slots) == 8
    assert [slot.local_date.isoformat() for slot in slots] == [
        "2026-11-06",
        "2026-11-07",
        "2026-11-09",
        "2026-11-11",
        "2026-11-13",
        "2026-11-14",
        "2026-11-16",
        "2026-11-18",
    ]
    assert slots[0].scheduled_at_ms == 1_793_930_400_000
    assert slots[1].lane == "special"
    assert all(slot.local_time == "09:00" and slot.timezone == "Asia/Ho_Chi_Minh" for slot in slots)
    assert all(slot.deadline_at_ms - slot.scheduled_at_ms == 30 * 60_000 for slot in slots)


def test_plan_slots_uses_half_open_date_horizon_and_validates_policy() -> None:
    calendar = BusinessCalendar("Asia/Ho_Chi_Minh")
    assert plan_slots(POLICY, date(2026, 11, 9), 1, calendar)[0].local_date == date(2026, 11, 9)
    assert plan_slots(POLICY, date(2026, 11, 10), 1, calendar) == []


def test_channel_identity_and_config_hash_are_stable_and_secret_free() -> None:
    channel = Channel(
        id="channel-synthetic-1",
        project_id="venho_hotel",
        environment="production",
        channel_key="fb_hanoi",
        platform=ChannelPlatform.FACEBOOK,
        remote_account_id="account-synthetic-1",
        name="Synthetic Facebook Page",
    )
    left = ChannelConfig(
        id="config-1",
        channel_id=channel.id,
        version=1,
        make_route_ref="route-fb-hanoi",
        graph_api_version="vNN.N",
        capability={"receipts.write": True, "media.read": True},
    )
    reordered = ChannelConfig(
        id="config-2",
        channel_id=channel.id,
        version=1,
        make_route_ref="route-fb-hanoi",
        graph_api_version="vNN.N",
        capability={"media.read": True, "receipts.write": True},
    )
    changed = ChannelConfig(
        id="config-3",
        channel_id=channel.id,
        version=2,
        make_route_ref="route-fb-venho",
        graph_api_version="vNN.N",
        capability={"media.read": True, "receipts.write": True},
    )
    assert len(config_hash(left)) == 64
    assert config_hash(left) == config_hash(reordered)
    assert config_hash(left) != config_hash(changed)
