from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PublishingPolicy:
    window_minutes: int
    grant_ttl_seconds: int
    receipt_grace_minutes: int
    redeliver_after_ack_minutes: int
    max_transport_attempts: int
    verify_delay_minutes: int
    unknown_escalation_minutes: int

    def __post_init__(self) -> None:
        for name in (
            "window_minutes",
            "grant_ttl_seconds",
            "receipt_grace_minutes",
            "redeliver_after_ack_minutes",
            "max_transport_attempts",
            "verify_delay_minutes",
            "unknown_escalation_minutes",
        ):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True)
class PublishWindow:
    scheduled_at_ms: int
    deadline_at_ms: int

    def __post_init__(self) -> None:
        if type(self.scheduled_at_ms) is not int or type(self.deadline_at_ms) is not int:
            raise ValueError("window timestamps must be integer epoch milliseconds")
        if self.deadline_at_ms < self.scheduled_at_ms:
            raise ValueError("deadline must not precede scheduled time")

    @classmethod
    def for_scheduled(
        cls, scheduled_at_ms: int, policy: PublishingPolicy
    ) -> PublishWindow:
        return cls(
            scheduled_at_ms=scheduled_at_ms,
            deadline_at_ms=scheduled_at_ms + policy.window_minutes * 60_000,
        )

    def is_open(self, now_ms: int) -> bool:
        return type(now_ms) is int and self.scheduled_at_ms <= now_ms <= self.deadline_at_ms

    def is_expired(self, now_ms: int) -> bool:
        return type(now_ms) is int and now_ms > self.deadline_at_ms


@dataclass(frozen=True)
class GrantWindow:
    grant_expires_at_ms: int
    receipt_due_at_ms: int


def grant_window(
    now_ms: int,
    deadline_at_ms: int,
    ttl_seconds: int = 60,
    receipt_grace_minutes: int = 15,
) -> GrantWindow:
    for name, value in (
        ("now_ms", now_ms),
        ("deadline_at_ms", deadline_at_ms),
        ("ttl_seconds", ttl_seconds),
        ("receipt_grace_minutes", receipt_grace_minutes),
    ):
        if type(value) is not int:
            raise ValueError(f"{name} must be an integer")
    if deadline_at_ms < now_ms or ttl_seconds <= 0 or receipt_grace_minutes < 0:
        raise ValueError("invalid grant window bounds")
    grant_expires_at_ms = min(now_ms + ttl_seconds * 1_000, deadline_at_ms)
    return GrantWindow(
        grant_expires_at_ms=grant_expires_at_ms,
        receipt_due_at_ms=grant_expires_at_ms + receipt_grace_minutes * 60_000,
    )
