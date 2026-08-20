from __future__ import annotations

from typing import Protocol

from ...domain.policies.promotion import QcResult


class QcGatewayPort(Protocol):
    def validate(self, composite_path: str, a2_path: str) -> QcResult:
        """WRAP the existing validator_studio. Behaviour must not change.
        Default samples=3 (fixes the non-determinism found 2026-07-17).
        This Port must not contain any threshold — thresholds belong to 07F."""
        ...
