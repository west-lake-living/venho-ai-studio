from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# Contract table: v2.0 plan PHẦN 5.2 / PHẦN 8.5. Codes are structured — never
# raw vendor stack traces or env content cross into RestorationResult (lesson
# from the 2026-07-17 OPENAI_API_KEY stdout leak, see PHẦN 11).
ErrorCode = Literal[
    "ERR_GW_A2_HASH_MISMATCH",
    "ERR_GW_WORKER_OFFLINE",
    "ERR_GW_WORKER_TIMEOUT",
    "ERR_GW_VRAM_EXHAUSTED",
    "ERR_GW_WORKFLOW_INVALID",
    "ERR_GW_NODE_BINDING_FAILED",
    "ERR_GW_UPLOAD_FAILED",
    "ERR_GW_EMPTY_OUTPUT",
    "ERR_GW_GEOMETRY_MISMATCH",
    "ERR_GW_PIXEL_LOCK_VIOLATED",
    "ERR_GW_LEASE_UNAVAILABLE",
    "ERR_GW_CANCELLED",
    "ERR_GW_QC_NOT_CONFIGURED",
    "ERR_GW_QC_CONTRACT_INVALID",
    "ERR_GW_QC_OWNERSHIP_MISMATCH",
    "ERR_GW_QC_ARTIFACT_MISSING",
    "ERR_GW_QC_A2_MISSING",
    "ERR_GW_QC_VALIDATION",
]


@dataclass
class RestorationError(Exception):
    """Structured failure. Adapters must raise this, never a bare library error."""

    code: ErrorCode
    message: str
    retryable: bool = False

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.code}: {self.message}"
