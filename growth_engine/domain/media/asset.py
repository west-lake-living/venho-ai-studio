from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class VariantQcStatus(str, Enum):
    PENDING = "PENDING"
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"
    QUARANTINED = "QUARANTINED"


@dataclass(frozen=True)
class MediaAsset:
    id: str
    source_type: str
    source_ref: str
    source_revision: str
    source_sha256: str
    original_key: str
    metadata_json: str
    created_at_ms: int

    def __post_init__(self) -> None:
        for name in ("id", "source_ref", "source_revision", "original_key", "metadata_json"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} is required")
        if self.source_type not in {"ai_generated", "library", "upload", "fallback", "legacy"}:
            raise ValueError("source_type is invalid")
        _validate_sha256(self.source_sha256, "source_sha256")
        if type(self.created_at_ms) is not int:
            raise ValueError("created_at_ms must be integer epoch milliseconds")


@dataclass(frozen=True)
class MediaVariant:
    id: str
    asset_id: str
    transform_version: str
    sha256: str
    object_key: str
    width: int
    height: int
    mime: str
    byte_size: int
    qc_status: VariantQcStatus
    created_at_ms: int

    def __post_init__(self) -> None:
        for name in ("id", "asset_id", "transform_version", "object_key"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} is required")
        _validate_sha256(self.sha256, "sha256")
        if any(type(value) is not int or value <= 0 for value in (self.width, self.height, self.byte_size)):
            raise ValueError("variant dimensions and byte_size must be positive integers")
        if self.mime != "image/jpeg":
            raise ValueError("media variants must be JPEG")
        if type(self.created_at_ms) is not int:
            raise ValueError("created_at_ms must be integer epoch milliseconds")


def _validate_sha256(value: str, name: str) -> None:
    if len(value) != 64 or any(char not in "0123456789abcdefABCDEF" for char in value):
        raise ValueError(f"{name} must be a 64-character SHA-256 hex digest")
