from __future__ import annotations

from dataclasses import dataclass, field

from ...application.ports.clock import ClockPort
from ...application.ports.worker_health import WorkerHealth, WorkerHealthPort, WorkerStatus

# GW-E12: without this, a dead worker produces N consecutive job failures
# instead of failing fast at job 1. TTL default 30s. Circuit breaker: 3
# consecutive OFFLINE probes opens the circuit for 5 minutes — after that,
# probe() returns OFFLINE immediately with no network call, instead of
# hanging every job for ~timeout_s for nothing (v2.0 PHẦN 8.4).


@dataclass
class CachedWorkerHealth:
    inner: WorkerHealthPort
    clock: ClockPort
    ttl_seconds: float = 30.0
    breaker_threshold: int = 3
    breaker_open_seconds: float = 300.0

    _cached: WorkerHealth | None = field(default=None, init=False, repr=False)
    _cached_at: float = field(default=float("-inf"), init=False, repr=False)
    _consecutive_offline: int = field(default=0, init=False, repr=False)
    _breaker_opened_at: float | None = field(default=None, init=False, repr=False)

    def probe(self) -> WorkerHealth:
        now = self.clock.monotonic()

        if self._breaker_opened_at is not None:
            if now - self._breaker_opened_at < self.breaker_open_seconds:
                return WorkerHealth(status=WorkerStatus.OFFLINE)
            self._breaker_opened_at = None
            self._consecutive_offline = 0

        if self._cached is not None and (now - self._cached_at) < self.ttl_seconds:
            return self._cached

        result = self.inner.probe()
        self._cached = result
        self._cached_at = now

        if result.status is WorkerStatus.OFFLINE:
            self._consecutive_offline += 1
            if self._consecutive_offline >= self.breaker_threshold:
                self._breaker_opened_at = now
        else:
            self._consecutive_offline = 0

        return result
