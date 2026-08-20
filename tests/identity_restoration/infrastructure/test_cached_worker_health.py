from __future__ import annotations

from dataclasses import dataclass

from identity_restoration.application.ports.worker_health import WorkerHealth, WorkerStatus
from identity_restoration.infrastructure.health.cached_worker_health import CachedWorkerHealth


@dataclass
class FakeClock:
    t: float = 0.0

    def now(self):
        return None

    def monotonic(self) -> float:
        return self.t


class ScriptedProbe:
    def __init__(self, results: list[WorkerHealth]) -> None:
        self._results = list(results)
        self.call_count = 0

    def probe(self) -> WorkerHealth:
        self.call_count += 1
        return self._results.pop(0)


def test_result_is_cached_within_ttl() -> None:
    clock = FakeClock(t=0.0)
    probe = ScriptedProbe([WorkerHealth(status=WorkerStatus.HEALTHY)] * 3)
    cached = CachedWorkerHealth(inner=probe, clock=clock, ttl_seconds=30.0)

    cached.probe()
    clock.t = 10.0
    cached.probe()

    assert probe.call_count == 1  # second call served from cache


def test_result_refreshes_after_ttl_expires() -> None:
    clock = FakeClock(t=0.0)
    probe = ScriptedProbe([WorkerHealth(status=WorkerStatus.HEALTHY)] * 3)
    cached = CachedWorkerHealth(inner=probe, clock=clock, ttl_seconds=30.0)

    cached.probe()
    clock.t = 31.0
    cached.probe()

    assert probe.call_count == 2


def test_circuit_opens_after_threshold_consecutive_offline_and_skips_probe() -> None:
    clock = FakeClock(t=0.0)
    probe = ScriptedProbe([WorkerHealth(status=WorkerStatus.OFFLINE)] * 3)
    cached = CachedWorkerHealth(inner=probe, clock=clock, ttl_seconds=0.0, breaker_threshold=3,
                                breaker_open_seconds=300.0)

    for i in range(3):
        clock.t = float(i * 100)
        result = cached.probe()
        assert result.status is WorkerStatus.OFFLINE

    assert probe.call_count == 3
    clock.t = 350.0  # still inside the open-circuit window
    result = cached.probe()
    assert result.status is WorkerStatus.OFFLINE
    assert probe.call_count == 3  # circuit open: no new network probe


def test_circuit_closes_after_open_window_elapses() -> None:
    clock = FakeClock(t=0.0)
    probe = ScriptedProbe(
        [WorkerHealth(status=WorkerStatus.OFFLINE)] * 3 + [WorkerHealth(status=WorkerStatus.HEALTHY)]
    )
    cached = CachedWorkerHealth(inner=probe, clock=clock, ttl_seconds=0.0, breaker_threshold=3,
                                breaker_open_seconds=100.0)
    for i in range(3):
        clock.t = float(i * 200)
        cached.probe()

    clock.t = 1000.0  # well past the 100s open window
    result = cached.probe()
    assert result.status is WorkerStatus.HEALTHY
    assert probe.call_count == 4
