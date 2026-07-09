from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional


@dataclass
class CircuitState:
    state: str = "CLOSED"
    failure_count: int = 0
    opened_at: Optional[datetime] = None


@dataclass
class CircuitBreaker:
    failure_threshold: int = 3
    cooldown_seconds: int = 60
    states: Dict[str, CircuitState] = field(default_factory=dict)

    def state_for(self, platform: str, now: Optional[datetime] = None) -> str:
        current = now or datetime.now(timezone.utc)
        state = self.states.setdefault(platform, CircuitState())
        if state.state == "OPEN" and state.opened_at:
            if current - state.opened_at >= timedelta(seconds=self.cooldown_seconds):
                state.state = "HALF_OPEN"
        return state.state

    def allow(self, platform: str, now: Optional[datetime] = None) -> bool:
        return self.state_for(platform, now=now) != "OPEN"

    def record_success(self, platform: str) -> None:
        self.states[platform] = CircuitState()

    def record_failure(self, platform: str, now: Optional[datetime] = None) -> None:
        current = now or datetime.now(timezone.utc)
        state = self.states.setdefault(platform, CircuitState())
        state.failure_count += 1
        if state.failure_count >= self.failure_threshold:
            state.state = "OPEN"
            state.opened_at = current
