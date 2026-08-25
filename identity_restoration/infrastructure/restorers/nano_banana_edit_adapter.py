from __future__ import annotations

"""Adapter for the existing Venho OS Nano Banana masked-edit capability.

This module intentionally does not import an SDK or construct a provider. The
Venho OS composition root owns ``GenerateStudioImageUseCase`` and
``GeminiImageProvider``. It supplies their already-built masked-edit boundary
here when the two runtimes are connected by the application composition root.
"""

from dataclasses import dataclass
from typing import Any, Mapping

from ...application.benchmark_executor import (
    NanoBananaEditPort,
    NanoBananaEditRequest,
    NanoBananaEditResult,
)


@dataclass(frozen=True)
class NanoBananaEditAdapter(NanoBananaEditPort):
    """Thin delegation adapter; all generation remains in ``production_path``."""

    production_path: NanoBananaEditPort

    def capabilities(self) -> Mapping[str, Any]:
        capabilities = self.production_path.capabilities()
        if not isinstance(capabilities, Mapping):
            return {
                "ready": False,
                "providerConfigured": False,
                "fallbackEnabled": False,
                "blockers": ["existing Nano Banana production capability is malformed"],
            }
        return {
            **dict(capabilities),
            "adapterPath": f"{__name__}.NanoBananaEditAdapter",
            "productionPathReused": True,
            "fallbackEnabled": bool(capabilities.get("fallbackEnabled", False)),
        }

    def masked_edit(
        self, request: NanoBananaEditRequest, *, run_id: str, attempt_id: str
    ) -> NanoBananaEditResult:
        return self.production_path.masked_edit(request, run_id=run_id, attempt_id=attempt_id)
