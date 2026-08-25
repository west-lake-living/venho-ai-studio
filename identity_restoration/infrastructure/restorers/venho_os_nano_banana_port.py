from __future__ import annotations

"""Fail-closed transport to the existing VenHo OS Nano production use-case.

This is a transport port, not a provider implementation.  The server-side
endpoint assembles the existing GenerateStudioImageUseCase and
GeminiImageProvider; this module only exchanges the already-resolved masked
edit command and sanitized result metadata.
"""

import base64
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ...application.benchmark_executor import (
    NanoBananaEditPort,
    NanoBananaEditRequest,
    NanoBananaEditResult,
)


@dataclass(frozen=True)
class VenhoOsNanoBananaPort(NanoBananaEditPort):
    endpoint: str
    timeout_seconds: float = 900.0

    def capabilities(self) -> Mapping[str, Any]:
        try:
            payload = self._request("GET", None)
        except Exception as exc:
            return {
                "ready": False,
                "providerConfigured": False,
                "fallbackEnabled": False,
                "adapterPath": f"{__name__}.VenhoOsNanoBananaPort",
                "provider": "nano-banana-2",
                "model": "gemini-3.1-flash-image",
                "blockers": [f"existing VenHo OS Nano endpoint unavailable: {exc}"],
            }
        if not isinstance(payload, Mapping):
            return {
                "ready": False,
                "providerConfigured": False,
                "fallbackEnabled": False,
                "blockers": ["existing VenHo OS Nano capability response is malformed"],
            }
        return dict(payload)

    def masked_edit(
        self, request: NanoBananaEditRequest, *, run_id: str, attempt_id: str
    ) -> NanoBananaEditResult:
        if request.mask_path is None:
            raise RuntimeError("Nano bridge requires a full-canvas mask")
        payload = {
            "runId": run_id,
            "attemptId": attempt_id,
            "basePath": str(request.base_path),
            "maskPath": str(request.mask_path),
            "a2Path": str(request.a2_path),
            "cropTransform": dict(request.crop_transform or {}),
            "maskVersion": request.mask_version,
            "geometryAuthorityPath": str(request.geometry_authority_path)
            if request.geometry_authority_path
            else None,
            "lineage": dict(request.lineage or {}),
        }
        started = time.monotonic()
        response = self._request("POST", payload)
        if not isinstance(response, Mapping):
            raise RuntimeError("existing VenHo OS Nano response is malformed")
        image_b64 = response.get("imageBase64")
        if not isinstance(image_b64, str) or not image_b64:
            raise RuntimeError(str(response.get("error", "Nano response has no image")))
        try:
            image_bytes = base64.b64decode(image_b64, validate=True)
        except Exception as exc:
            raise RuntimeError("Nano response imageBase64 is malformed") from exc
        metadata = response.get("metadata")
        metadata = dict(metadata) if isinstance(metadata, Mapping) else {}
        return NanoBananaEditResult(
            image_bytes=image_bytes,
            provider_id=str(response.get("provider", "")),
            model_id=str(response.get("model", "")),
            provider_request_id=_optional_str(response.get("providerRequestId")),
            provider_run_id=_optional_str(response.get("providerRunId")),
            runtime_ms=int(response.get("runtimeMs", round((time.monotonic() - started) * 1000))),
            retry_count=int(response.get("retryCount", 0)),
            seed_supported=bool(response.get("seedSupported", False)),
            backend=_optional_str(response.get("backend")),
            host=dict(response.get("host")) if isinstance(response.get("host"), Mapping) else None,
            mock_used=bool(response.get("mockUsed", False)),
            local_fallback=bool(response.get("localFallback", False)),
            silent_fallback=bool(response.get("silentFallback", False)),
            provider_metadata=metadata,
        )

    def _request(self, method: str, payload: Mapping[str, Any] | None) -> Any:
        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload, sort_keys=True).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.endpoint, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Nano bridge HTTP {exc.code}: {detail[:500]}") from exc
        return json.loads(raw.decode("utf-8"))


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None
