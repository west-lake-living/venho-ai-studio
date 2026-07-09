"""Shared exception types and error codes for Publishing Gateway."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


ERR_APPROVAL_REQUIRED = "ERR_APPROVAL_REQUIRED"
ERR_APPROVAL_INVALID = "ERR_APPROVAL_INVALID"
ERR_APPROVAL_EXPIRED = "ERR_APPROVAL_EXPIRED"
ERR_DUPLICATE_PUBLISH = "ERR_DUPLICATE_PUBLISH"
ERR_BRAND_DISPLAY_VIOLATION = "ERR_BRAND_DISPLAY_VIOLATION"
ERR_CONTRACT_INVALID = "ERR_CONTRACT_INVALID"
ERR_PLATFORM_DISABLED = "ERR_PLATFORM_DISABLED"
ERR_PLATFORM_CAPABILITY = "ERR_PLATFORM_CAPABILITY"
ERR_TOKEN_INVALID = "ERR_TOKEN_INVALID"
ERR_RATE_LIMITED = "ERR_RATE_LIMITED"
ERR_CIRCUIT_OPEN = "ERR_CIRCUIT_OPEN"
ERR_ADAPTER_FAILED = "ERR_ADAPTER_FAILED"


@dataclass
class PublishingGatewayError(Exception):
    """Base error carrying a stable code for receipts and CLI output."""

    message: str
    code: str = ERR_ADAPTER_FAILED

    known_codes: ClassVar[set[str]] = {
        ERR_APPROVAL_REQUIRED,
        ERR_APPROVAL_INVALID,
        ERR_APPROVAL_EXPIRED,
        ERR_DUPLICATE_PUBLISH,
        ERR_BRAND_DISPLAY_VIOLATION,
        ERR_CONTRACT_INVALID,
        ERR_PLATFORM_DISABLED,
        ERR_PLATFORM_CAPABILITY,
        ERR_TOKEN_INVALID,
        ERR_RATE_LIMITED,
        ERR_CIRCUIT_OPEN,
        ERR_ADAPTER_FAILED,
    }

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"
