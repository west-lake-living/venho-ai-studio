from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Protocol, Sequence

from growth_engine.application.ports.clock import Clock
from growth_engine.application.scheduling.reserve_target import TargetAlreadyReserved
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.states import LIVE, DeliveryState


_TOPIC_DEDUPE_MS = 120 * 24 * 60 * 60 * 1000


@dataclass(frozen=True)
class LaneTarget:
    target_id: str
    slot_id: str
    channel_id: str
    lane: str
    delivery: Delivery | None = None
    live_execution: bool = False

    def __post_init__(self) -> None:
        for name in ("target_id", "slot_id", "channel_id", "lane"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} is required")
        if self.delivery is not None and not isinstance(self.delivery, Delivery):
            raise ValueError("delivery must be a Delivery or None")
        if type(self.live_execution) is not bool:
            raise ValueError("live_execution must be a boolean")


@dataclass(frozen=True)
class LanePackage:
    package_id: str
    topic_key: str

    def __post_init__(self) -> None:
        if not self.package_id.strip() or not self.topic_key.strip():
            raise ValueError("package_id and topic_key are required")


@dataclass(frozen=True)
class LaneRunResult:
    lane: str
    reserved_target_ids: tuple[str, ...] = ()
    skipped_target_ids: tuple[str, ...] = ()
    raced_target_ids: tuple[str, ...] = ()
    duplicate_topic_slot_ids: tuple[str, ...] = ()


class RunLanesStore(Protocol):
    """Read and slot-creation seam for weekly, fast, and replacement generation."""

    def ensure_slots(self, now_ms: int, *, horizon_days: int) -> object: ...
    def select_targets(self, lane: str, *, now_ms: int, horizon_days: int) -> Sequence[LaneTarget]: ...
    def list_recent_topic_keys(self, since_ms: int) -> Sequence[str]: ...
    def refresh_target(self, target_id: str) -> LaneTarget | None: ...


class LanePackageFactory(Protocol):
    def create(
        self,
        slot_id: str,
        lane: str,
        *,
        excluded_topic_keys: tuple[str, ...],
    ) -> LanePackage: ...


class ReserveTargetUseCase(Protocol):
    def execute(
        self,
        target_id: str,
        *,
        package_id: str,
        lane: str,
        correlation_id: str,
    ) -> object: ...


class RunLanes:
    """Coordinate package generation and D01 target reservations for each content lane."""

    def __init__(
        self,
        store: RunLanesStore,
        packages: LanePackageFactory,
        reserve_target: ReserveTargetUseCase,
        clock: Clock,
    ) -> None:
        self._store = store
        self._packages = packages
        self._reserve_target = reserve_target
        self._clock = clock

    def run_weekly(self, *, horizon_days: int = 14) -> LaneRunResult:
        self._validate_horizon(horizon_days)
        now_ms = self._clock.now_ms()
        self._store.ensure_slots(now_ms, horizon_days=horizon_days)
        return self._run("weekly", now_ms=now_ms, horizon_days=horizon_days)

    def run_fast(self, *, horizon_days: int = 14) -> LaneRunResult:
        self._validate_horizon(horizon_days)
        return self._run("fast", now_ms=self._clock.now_ms(), horizon_days=horizon_days)

    def run_replacement(self, *, horizon_days: int = 14) -> LaneRunResult:
        self._validate_horizon(horizon_days)
        return self._run("replacement", now_ms=self._clock.now_ms(), horizon_days=horizon_days)

    def _run(self, lane: str, *, now_ms: int, horizon_days: int) -> LaneRunResult:
        targets = self._store.select_targets(lane, now_ms=now_ms, horizon_days=horizon_days)
        by_slot: dict[str, list[LaneTarget]] = defaultdict(list)
        skipped: list[str] = []
        for target in sorted(targets, key=lambda item: (item.slot_id, item.channel_id, item.target_id)):
            if not _safe_to_reserve(target):
                skipped.append(target.target_id)
                continue
            by_slot[target.slot_id].append(target)

        recent_topics = set(self._store.list_recent_topic_keys(now_ms - _TOPIC_DEDUPE_MS))
        reserved: list[str] = []
        raced: list[str] = []
        duplicate_slots: list[str] = []
        for slot_id in sorted(by_slot):
            slot_targets = by_slot[slot_id]
            slot_lanes = {target.lane for target in slot_targets}
            if len(slot_lanes) != 1:
                raise ValueError("targets in a slot must share the slot lane")
            slot_lane = next(iter(slot_lanes))
            excluded = tuple(sorted(recent_topics))
            package = self._packages.create(slot_id, slot_lane, excluded_topic_keys=excluded)
            if package.topic_key in recent_topics:
                duplicate_slots.append(slot_id)
                continue
            recent_topics.add(package.topic_key)
            correlation_id = f"lane:{lane}:{slot_id}:{now_ms}"
            for target in slot_targets:
                try:
                    self._reserve_target.execute(
                        target.target_id,
                        package_id=package.package_id,
                        lane=target.lane,
                        correlation_id=correlation_id,
                    )
                except TargetAlreadyReserved:
                    # Re-read the winner and stop here: this race never creates a new slot.
                    self._store.refresh_target(target.target_id)
                    raced.append(target.target_id)
                    continue
                reserved.append(target.target_id)

        return LaneRunResult(
            lane=lane,
            reserved_target_ids=tuple(reserved),
            skipped_target_ids=tuple(skipped),
            raced_target_ids=tuple(raced),
            duplicate_topic_slot_ids=tuple(duplicate_slots),
        )

    @staticmethod
    def _validate_horizon(horizon_days: int) -> None:
        if type(horizon_days) is not int or horizon_days < 0:
            raise ValueError("horizon_days must be a non-negative integer")


def _safe_to_reserve(target: LaneTarget) -> bool:
    if target.live_execution:
        return False
    if target.delivery is None:
        return True
    if target.delivery.state in LIVE or target.delivery.state is DeliveryState.PUBLISHED:
        return False
    return target.delivery.state is DeliveryState.SUPERSEDED
