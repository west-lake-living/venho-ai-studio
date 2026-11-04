from __future__ import annotations

from contextlib import contextmanager
from datetime import date

import pytest

from growth_engine.application.errors import ApplicationError
from growth_engine.application.scheduling.ensure_slots import (
    ChannelAvailability,
    EnsureSlots,
)
from growth_engine.application.scheduling.reserve_target import (
    ReserveTarget,
    TargetAlreadyReserved,
)
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.states import DeliveryState
from growth_engine.domain.scheduling.cadence import CadencePolicy, CadenceRule
from growth_engine.domain.scheduling.slot import Slot, SlotTarget


class FakeClock:
    def now_ms(self):
        return 1_798_000_000_000


class SequentialIds:
    def __init__(self):
        self.value = 0

    def new_id(self):
        self.value += 1
        return f"id-{self.value}"


class FakeSlotStore:
    def __init__(self, channels):
        self.channels = channels
        self.slots = {}
        self.targets = {}
        self.incidents = set()
        self.audit = []

    @contextmanager
    def begin_immediate(self):
        yield self

    def list_channels(self, project_id, environment):
        return [channel for channel in self.channels if channel.project_id == project_id and channel.environment == environment]

    def find_slot(self, project_id, local_date, local_time, lane):
        return self.slots.get((project_id, local_date, local_time, lane))

    def insert_slot_if_absent(self, slot, *, created_at_ms):
        key = (slot.project_id, slot.local_date, slot.local_time, slot.lane)
        if key in self.slots:
            return False
        self.slots[key] = slot
        return True

    def find_target(self, slot_id, channel_id):
        return self.targets.get((slot_id, channel_id))

    def insert_target_if_absent(self, target):
        key = (target.slot_id, target.channel_id)
        if key in self.targets:
            return False
        self.targets[key] = target
        return True

    def open_channel_config_incident(self, channel_id, *, now_ms, correlation_id):
        self.incidents.add(channel_id)

    def append_audit(self, **entry):
        self.audit.append(entry)


def _policy():
    return CadencePolicy(
        version=2,
        project_id="venho_hotel",
        timezone="Asia/Ho_Chi_Minh",
        publish_time="09:00",
        rules=(
            CadenceRule(0, "regular", "monday"),
            CadenceRule(2, "regular", "wednesday"),
            CadenceRule(4, "regular", "friday"),
            CadenceRule(5, "special", "saturday"),
        ),
        window_minutes=30,
    )


def test_ensure_slots_creates_target_for_each_enabled_page_and_is_idempotent():
    store = FakeSlotStore(
        [
            ChannelAvailability("page-a", "venho_hotel", "production", enabled=True, configured=True),
            ChannelAvailability("page-b", "venho_hotel", "production", enabled=True, configured=True),
        ]
    )
    use_case = EnsureSlots(store, FakeClock(), SequentialIds())

    first = use_case.execute(
        _policy(),
        start_date=date(2026, 11, 2),
        horizon_days=7,
        environment="production",
        correlation_id="ensure-1",
    )
    second = use_case.execute(
        _policy(),
        start_date=date(2026, 11, 2),
        horizon_days=7,
        environment="production",
        correlation_id="ensure-2",
    )

    assert first.slots_created == 4
    assert first.targets_created == 8
    assert second.slots_created == 0
    assert second.targets_created == 0
    assert len(store.slots) == 4
    assert len(store.targets) == 8


def test_ensure_slots_records_unconfigured_enabled_channel_instead_of_skipping_silently():
    channel = ChannelAvailability("page-unconfigured", "venho_hotel", "production", enabled=True, configured=False)
    store = FakeSlotStore([channel])

    result = EnsureSlots(store, FakeClock(), SequentialIds()).execute(
        _policy(),
        start_date=date(2026, 11, 2),
        horizon_days=1,
        environment="production",
        correlation_id="ensure-unconfigured",
    )

    assert result.targets_created == 1
    assert result.unconfigured_channel_ids == ("page-unconfigured",)
    assert store.incidents == {"page-unconfigured"}


class FakeReservationStore:
    def __init__(self, slot, target, *, race=False):
        self.slot = slot
        self.target = target
        self.delivery = None
        self.race = race
        self.audit = []

    @contextmanager
    def begin_immediate(self):
        yield self

    def load_target_context(self, target_id):
        assert target_id == self.target.id
        return {"slot": self.slot, "target": self.target, "active_delivery": self.delivery}

    def insert_draft_delivery(self, delivery, *, target, package_id, created_at_ms):
        if self.race:
            self.delivery = Delivery("race-delivery", DeliveryState.DRAFT)
            return False
        self.delivery = delivery
        return True

    def append_audit(self, **entry):
        self.audit.append(entry)


def test_reserve_target_creates_draft_and_unique_race_returns_target_taken():
    slot = Slot(
        id="slot-1",
        project_id="venho_hotel",
        local_date=date(2026, 11, 2),
        local_time="09:00",
        timezone="Asia/Ho_Chi_Minh",
        lane="monday",
        cadence_version="2",
        scheduled_at_ms=1_798_000_000_000,
        deadline_at_ms=1_798_001_800_000,
    )
    target = SlotTarget("target-1", slot.id, "page-a")
    store = FakeReservationStore(slot, target)
    result = ReserveTarget(store, FakeClock(), SequentialIds()).execute(
        target.id,
        package_id="package-1",
        lane="monday",
        correlation_id="reserve-1",
    )
    assert result.state is DeliveryState.DRAFT
    assert store.delivery == result

    race_store = FakeReservationStore(slot, target, race=True)
    with pytest.raises(TargetAlreadyReserved) as raised:
        ReserveTarget(race_store, FakeClock(), SequentialIds()).execute(
            target.id,
            package_id="package-1",
            lane="monday",
            correlation_id="reserve-2",
        )
    assert raised.value.code == "ERR_GC2_TARGET_TAKEN"
    assert race_store.delivery.id == "race-delivery"


def test_reserve_target_refuses_cancelled_slot_and_existing_active_delivery():
    slot = Slot(
        id="slot-1",
        project_id="venho_hotel",
        local_date=date(2026, 11, 2),
        local_time="09:00",
        timezone="Asia/Ho_Chi_Minh",
        lane="monday",
        cadence_version="2",
        scheduled_at_ms=1_798_000_000_000,
        deadline_at_ms=1_798_001_800_000,
        cancelled_at_ms=1_797_900_000_000,
    )
    target = SlotTarget("target-1", slot.id, "page-a")
    with pytest.raises(ApplicationError):
        ReserveTarget(FakeReservationStore(slot, target), FakeClock(), SequentialIds()).execute(
            target.id,
            package_id="package-1",
            lane="monday",
            correlation_id="reserve-cancelled",
        )

    active_slot = Slot(
        id="slot-2",
        project_id="venho_hotel",
        local_date=date(2026, 11, 2),
        local_time="09:00",
        timezone="Asia/Ho_Chi_Minh",
        lane="monday",
        cadence_version="2",
        scheduled_at_ms=1_798_000_000_000,
        deadline_at_ms=1_798_001_800_000,
    )
    active_target = SlotTarget("target-2", active_slot.id, "page-a")
    active_store = FakeReservationStore(active_slot, active_target)
    active_store.delivery = Delivery("existing", DeliveryState.DRAFT)
    with pytest.raises(TargetAlreadyReserved):
        ReserveTarget(active_store, FakeClock(), SequentialIds()).execute(
            active_target.id,
            package_id="package-1",
            lane="monday",
            correlation_id="reserve-existing",
        )
