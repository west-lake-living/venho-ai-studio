from __future__ import annotations

from enum import Enum
from typing import Mapping


class ErrorCode(str, Enum):
    UNAUTHENTICATED = "ERR_GC2_UNAUTHENTICATED"
    FORBIDDEN = "ERR_GC2_FORBIDDEN"
    CAPABILITY_INVALID = "ERR_GC2_CAPABILITY_INVALID"
    NOT_FOUND = "ERR_GC2_NOT_FOUND"
    STATE_CONFLICT = "ERR_GC2_STATE_CONFLICT"
    ALREADY_AUTHORIZED = "ERR_GC2_ALREADY_AUTHORIZED"
    IDEMPOTENCY_MISMATCH = "ERR_GC2_IDEMPOTENCY_MISMATCH"
    TARGET_TAKEN = "ERR_GC2_TARGET_TAKEN"
    RECEIPT_CONFLICT = "ERR_GC2_RECEIPT_CONFLICT"
    REVISION_CONFLICT = "ERR_GC2_REVISION_CONFLICT"
    VALIDATION = "ERR_GC2_VALIDATION"
    QC_FAILED = "ERR_GC2_QC_FAILED"
    MEDIA_NOT_READY = "ERR_GC2_MEDIA_NOT_READY"
    MEDIA_REJECTED = "ERR_GC2_MEDIA_REJECTED"
    FACT_EXPIRED = "ERR_GC2_FACT_EXPIRED"
    DEADLINE_PASSED = "ERR_GC2_DEADLINE_PASSED"
    BUDGET_EXCEEDED = "ERR_GC2_BUDGET_EXCEEDED"
    PAYLOAD_TOO_LARGE = "ERR_GC2_PAYLOAD_TOO_LARGE"
    DB_BUSY = "ERR_GC2_DB_BUSY"
    DEPENDENCY_UNAVAILABLE = "ERR_GC2_DEPENDENCY_UNAVAILABLE"


class DomainError(Exception):
    def __init__(
        self,
        code: ErrorCode | str,
        message_vi: str,
        details: Mapping[str, object] | None = None,
    ) -> None:
        self.code = code.value if isinstance(code, ErrorCode) else str(code)
        self.message_vi = message_vi
        self.details = dict(details or {})
        super().__init__(message_vi)
