from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ReceiptOutcome(str, Enum):
    POST_CREATED = "POST_CREATED"
    REJECTED_NO_SIDE_EFFECT = "REJECTED_NO_SIDE_EFFECT"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"


def is_placeholder_post_id(value: str | None) -> bool:
    if not isinstance(value, str):
        return True
    normalized = value.strip()
    lowered = normalized.casefold()
    return (
        not normalized
        or lowered == "null"
        or "{{" in normalized
        or "}}" in normalized
        or lowered.startswith("test_")
    )


@dataclass(frozen=True)
class Receipt:
    issuer: str
    event_id: str
    execution_id: str
    grant_id: str
    command_id: str
    delivery_id: str
    revision_id: str
    channel_id: str
    remote_account_id: str
    payload_hash: str
    outcome: ReceiptOutcome
    platform_post_id: str | None = None
    error_class: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "issuer",
            "event_id",
            "execution_id",
            "grant_id",
            "command_id",
            "delivery_id",
            "revision_id",
            "channel_id",
            "remote_account_id",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
        if len(self.payload_hash) != 64 or any(
            char not in "0123456789abcdefABCDEF" for char in self.payload_hash
        ):
            raise ValueError("payload_hash must be a 64-character SHA-256 hex digest")
        if not isinstance(self.outcome, ReceiptOutcome):
            raise ValueError("outcome is invalid")
        if self.outcome is ReceiptOutcome.POST_CREATED and is_placeholder_post_id(self.platform_post_id):
            raise ValueError("POST_CREATED requires a non-placeholder platform_post_id")
        if self.outcome is ReceiptOutcome.REJECTED_NO_SIDE_EFFECT and not (self.error_class or "").strip():
            raise ValueError("rejected receipt requires an error_class")
