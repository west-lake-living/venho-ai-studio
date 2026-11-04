from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import date
from typing import Protocol, Sequence

from growth_engine.application.ports.clock import Clock, IdGenerator
from growth_engine.domain.kernel.hashing import canonical_json_bytes, sha256_hex
from growth_engine.domain.kernel.time import BusinessCalendar
from growth_engine.domain.scheduling.cadence import CadencePolicy, PlannedSlot, plan_slots
from growth_engine.domain.scheduling.slot import Slot, SlotTarget


@dataclass(frozen=True)
class ChannelAvailability:
    channel_id: str
    project_id: str
    environment: str
    enabled: bool
    configured: bool


@dataclass(frozen=True)
class EnsureSlotsResult:
    slots_created: int
    targets_created: int
    unconfigured_channel_ids: tuple[str, ...] = ()
    slot_ids: tuple[str, ...] = ()
    target_ids: tuple[str, ...] = ()


class EnsureSlotsTransaction(Protocol):
    def list_channels(self, project_id: str, environment: str) -> Sequence[ChannelAvailability]: ...
    def find_slot(self, project_id: str, local_date: date, local_time: str, lane: str) -> Slot | None: ...
    def insert_slot_if_absent(self, slot: Slot, *, created_at_ms: int) -> bool: ...
    def find_target(self, slot_id: str, channel_id: str) -> SlotTarget | None: ...
    def insert_target_if_absent(self, target: SlotTarget) -> bool: ...
    def open_channel_config_incident(self, channel_id: str, *, now_ms: int, correlation_id: str) -> None: ...
    def append_audit(self, **entry: object) -> None: ...


class EnsureSlotsStore(Protocol):
    def begin_immediate(self) -> AbstractContextManager[EnsureSlotsTransaction]: ...


class EnsureSlots:
    """Create cadence slots and every enabled channel target in one write transaction."""

    def __init__(self, store: EnsureSlotsStore, clock: Clock, ids: IdGenerator) -> None:
        self._store = store
        self._clock = clock
        self._ids = ids

    def execute(
        self,
        policy: CadencePolicy,
        *,
        start_date: date,
        horizon_days: int,
        environment: str,
        correlation_id: str,
    ) -> EnsureSlotsResult:
        if environment not in {"test", "production"}:
            raise ValueError("environment must be test or production")
        if not correlation_id.strip():
            raise ValueError("correlation_id is required")
        planned = plan_slots(policy, start_date, horizon_days, BusinessCalendar(policy.timezone))
        now_ms = self._clock.now_ms()
        created_slots: list[str] = []
        created_targets: list[str] = []
        unconfigured: set[str] = set()

        with self._store.begin_immediate() as tx:
            channels = [
                channel
                for channel in tx.list_channels(policy.project_id, environment)
                if channel.enabled
            ]
            if len({channel.channel_id for channel in channels}) != len(channels):
                raise ValueError("enabled channels contain duplicate ids")
            if any(
                channel.project_id != policy.project_id or channel.environment != environment
                for channel in channels
            ):
                raise ValueError("channel list crossed project or environment boundaries")
            for channel in channels:
                if not channel.configured:
                    unconfigured.add(channel.channel_id)
                    tx.open_channel_config_incident(
                        channel.channel_id,
                        now_ms=now_ms,
                        correlation_id=correlation_id,
                    )

            for candidate in planned:
                slot = tx.find_slot(
                    candidate.project_id,
                    candidate.local_date,
                    candidate.local_time,
                    candidate.lane,
                )
                if slot is None:
                    proposed = _slot_from_plan(candidate, self._ids.new_id())
                    if tx.insert_slot_if_absent(proposed, created_at_ms=now_ms):
                        slot = proposed
                        created_slots.append(slot.id)
                        tx.append_audit(
                            aggregate_type="slot",
                            aggregate_id=slot.id,
                            actor="growth-engine",
                            action="ensure_slot",
                            before_hash=None,
                            after_hash=_slot_hash(slot),
                            details={"lane": slot.lane, "local_date": slot.local_date.isoformat()},
                            correlation_id=correlation_id,
                            created_at_ms=now_ms,
                        )
                    else:
                        slot = tx.find_slot(
                            candidate.project_id,
                            candidate.local_date,
                            candidate.local_time,
                            candidate.lane,
                        )
                        if slot is None:
                            raise RuntimeError("slot insert lost a race but the winner could not be read")
                if slot.cancelled_at_ms is not None:
                    continue

                for channel in channels:
                    target = tx.find_target(slot.id, channel.channel_id)
                    if target is not None:
                        continue
                    proposed_target = SlotTarget(self._ids.new_id(), slot.id, channel.channel_id)
                    if tx.insert_target_if_absent(proposed_target):
                        created_targets.append(proposed_target.id)
                        tx.append_audit(
                            aggregate_type="slot_target",
                            aggregate_id=proposed_target.id,
                            actor="growth-engine",
                            action="ensure_slot_target",
                            before_hash=None,
                            after_hash=sha256_hex(
                                canonical_json_bytes(
                                    {
                                        "id": proposed_target.id,
                                        "slot_id": proposed_target.slot_id,
                                        "channel_id": proposed_target.channel_id,
                                        "required": proposed_target.required,
                                    }
                                )
                            ),
                            details={"slot_id": slot.id, "channel_id": channel.channel_id},
                            correlation_id=correlation_id,
                            created_at_ms=now_ms,
                        )
                    elif tx.find_target(slot.id, channel.channel_id) is None:
                        raise RuntimeError("target insert lost a race but the winner could not be read")

        return EnsureSlotsResult(
            slots_created=len(created_slots),
            targets_created=len(created_targets),
            unconfigured_channel_ids=tuple(sorted(unconfigured)),
            slot_ids=tuple(created_slots),
            target_ids=tuple(created_targets),
        )


def _slot_hash(slot: Slot) -> str:
    return sha256_hex(
        canonical_json_bytes(
            {
                "id": slot.id,
                "project_id": slot.project_id,
                "local_date": slot.local_date.isoformat(),
                "local_time": slot.local_time,
                "timezone": slot.timezone,
                "lane": slot.lane,
                "cadence_version": slot.cadence_version,
                "scheduled_at_ms": slot.scheduled_at_ms,
                "deadline_at_ms": slot.deadline_at_ms,
            }
        )
    )


def _slot_from_plan(candidate: PlannedSlot, slot_id: str) -> Slot:
    return Slot(
        id=slot_id,
        project_id=candidate.project_id,
        local_date=candidate.local_date,
        local_time=candidate.local_time,
        timezone=candidate.timezone,
        lane=candidate.lane,
        cadence_version=candidate.cadence_version,
        scheduled_at_ms=candidate.scheduled_at_ms,
        deadline_at_ms=candidate.deadline_at_ms,
    )
