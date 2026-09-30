"""Non-media readiness for the live face validator: config and runtime, never a Gemini call.

Callers (the faceless LAV capability gate) need to know the validator *can* run before any
paid generation starts, without paying for a probe. Each check is local:

- credential : GEMINI_API_KEY / GOOGLE_API_KEY present (value never printed)
- model      : effective GEMINI_VISION_MODEL equals the caller's pin and is not a floating alias
- policy     : transport attempts and paid-call guard limit parse to bounded positive ints;
               the provider's own request config keeps the 8192-token ceiling and thinking off
- config     : Face DNA and rubric 07F load for the project/subject
- runtime    : google-genai imports and the provider constructs (client creation is offline)
"""

from __future__ import annotations

import os
from typing import Any

from shared.vision.providers.gemini_vision import (
    DEFAULT_GEMINI_MODEL,
    MAX_TRANSPORT_ATTEMPTS_PER_LOGICAL_SAMPLE,
    GeminiVisionProvider,
    configured_transport_attempts,
)
from validator_studio.face_validator import _load_face_rubric
from validator_studio.utils import find_dna_path, load_json

MAX_OUTPUT_TOKENS = 8192


def _check(ok: bool, detail: str) -> dict[str, Any]:
    return {"ok": ok, "detail": detail}


def validator_health(project: str, subject: str, expected_model: str) -> dict[str, Any]:
    checks: dict[str, dict[str, Any]] = {}

    has_key = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    checks["credential"] = _check(has_key, "present" if has_key else "missing")

    model = os.environ.get("GEMINI_VISION_MODEL", DEFAULT_GEMINI_MODEL)
    pinned = model == expected_model and "latest" not in model
    checks["model"] = _check(pinned, model)

    try:
        attempts = configured_transport_attempts()
        max_calls = int(os.environ.get("VALIDATOR_MAX_NEW_CALLS", "12"))
        limits_ok = 1 <= attempts <= MAX_TRANSPORT_ATTEMPTS_PER_LOGICAL_SAMPLE and max_calls >= 1
        policy_detail = f"attempts={attempts} max_new_calls={max_calls}"
    except (RuntimeError, ValueError) as exc:
        limits_ok, policy_detail = False, type(exc).__name__

    try:
        dna = load_json(find_dna_path(project, subject))
        rubric = _load_face_rubric(project)
        config_ok = bool(dna) and bool(rubric)
        checks["config"] = _check(config_ok, f"dna_version={dna.get('dna_version')}")
    except Exception as exc:  # noqa: BLE001 - any load failure means not ready
        checks["config"] = _check(False, type(exc).__name__)

    runtime_ok = False
    runtime_detail = "not constructed"
    if has_key:
        try:
            provider = GeminiVisionProvider()
            config = provider._generate_config("health", None)
            runtime_ok = True
            runtime_detail = "provider constructed"
            limits_ok = (
                limits_ok
                and config.get("max_output_tokens") == MAX_OUTPUT_TOKENS
                and config.get("thinking_config", {}).get("thinking_budget") == 0
            )
            policy_detail += (
                f" max_output_tokens={config.get('max_output_tokens')}"
                f" thinking_budget={config.get('thinking_config', {}).get('thinking_budget')}"
            )
        except Exception as exc:  # noqa: BLE001
            runtime_detail = type(exc).__name__
    checks["policy"] = _check(limits_ok, policy_detail)
    checks["runtime"] = _check(runtime_ok, runtime_detail)

    ready = all(item["ok"] for item in checks.values())
    return {
        "status": "READY" if ready else "BLOCKED",
        "provider": "gemini",
        "subject": subject,
        "checks": checks,
        "gemini_calls": 0,
    }


__all__ = ["validator_health"]
