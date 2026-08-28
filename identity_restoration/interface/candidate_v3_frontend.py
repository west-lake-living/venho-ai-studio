"""Safe Candidate v3 frontend projection.

The frontend receives a deliberately small, redacted view of a job.  It never
needs artifact paths, configuration values, model details, or workflow
lineage.  Missing evidence is represented as ``UNVALIDATED`` so the view
cannot manufacture an approval state.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


class CandidateV3FrontendError(ValueError):
    """Raised when an unsafe value is about to cross the client boundary."""


_STATUSES = frozenset({"PASS", "FAIL", "NEEDS_REVIEW", "UNVALIDATED"})
_RETRYABLE_STATUSES = frozenset({"FAILED", "CANCELLED", "ORPHANED", "REVIEW_REQUIRED"})
_ROUTE_BASE_REGEN = "BASE_REGEN_REQUIRED"
_FORBIDDEN_KEY_PARTS = frozenset(
    {"path", "config", "workflow", "sha", "token", "secret", "model", "artifact", "bytes", "mask"}
)
_PUBLIC_RESULT_KEYS = frozenset(
    {
        "jobId",
        "runId",
        "attemptId",
        "status",
        "route",
        "routeReasons",
        "qualityStatus",
        "error",
        "profileId",
        "candidateProfileId",
        "identityPackId",
        "scenarioId",
        "preflight",
        "quality",
        "qualityScopes",
        "correctness",
    }
)


def validate_client_payload(payload: Mapping[str, Any]) -> None:
    """Fail closed unless a client payload contains identifiers and scalars only."""

    if not isinstance(payload, Mapping):
        raise CandidateV3FrontendError("CLIENT_PAYLOAD_MUST_BE_OBJECT")
    _validate_value(payload, "$")


def make_client_payload(action: str, **identifiers: str) -> dict[str, str]:
    """Build an action payload without allowing artifact/configuration inputs."""

    if not isinstance(action, str) or not action:
        raise CandidateV3FrontendError("CLIENT_ACTION_REQUIRED")
    payload = {"action": action}
    for key, value in identifiers.items():
        if not key or not key.endswith("Id") or not isinstance(value, str) or not value:
            raise CandidateV3FrontendError("CLIENT_PAYLOAD_IDS_ONLY")
        payload[key] = value
    validate_client_payload(payload)
    return payload


def redact_candidate_v3_client_result(result: Mapping[str, Any]) -> dict[str, Any]:
    """Project a service result into the only shape the frontend can consume."""

    if not isinstance(result, Mapping):
        raise CandidateV3FrontendError("CLIENT_RESULT_MUST_BE_OBJECT")
    projected: dict[str, Any] = {}
    for key in _PUBLIC_RESULT_KEYS:
        if key not in result:
            continue
        if key == "qualityScopes":
            projected[key] = _project_scopes(result[key])
        elif key == "correctness":
            projected[key] = _project_correctness(result[key])
        elif key == "quality":
            projected[key] = _project_merged_quality(result[key])
        elif key == "preflight":
            projected[key] = _project_preflight(result[key])
        elif key in {"routeReasons", "error"}:
            projected[key] = _safe_strings(result[key]) if key == "routeReasons" else _safe_text(result[key])
        else:
            projected[key] = _safe_scalar(result[key], key)
    return projected


def build_candidate_v3_ui_state(
    result: Mapping[str, Any],
    *,
    available_profile_ids: Sequence[str] = (),
    selected_profile_id: str | None = None,
    promotion_authorized: bool = False,
) -> dict[str, Any]:
    """Build deterministic frontend state from a redacted or service result."""

    public = redact_candidate_v3_client_result(result)
    profile_ids = _profile_ids(available_profile_ids)
    selected = selected_profile_id or _safe_optional_id(public.get("candidateProfileId"))
    if selected is not None and selected not in profile_ids:
        raise CandidateV3FrontendError("SELECTED_PROFILE_NOT_AVAILABLE")

    route = public.get("route")
    status = _safe_text(public.get("status")) or "UNKNOWN"
    quality_status = _quality_status(public)
    scopes = _ensure_required_scopes(public.get("qualityScopes"))
    correctness = public.get("correctness", {"status": "UNVALIDATED", "reasons": ["MISSING_CORRECTNESS_EVIDENCE"]})
    correctness_pass = correctness.get("status") == "PASS"
    scopes_pass = all(scope["status"] == "PASS" for scope in scopes.values())
    overall_pass = quality_status == "PASS" and correctness_pass and scopes_pass
    base_regeneration = route == _ROUTE_BASE_REGEN or status == _ROUTE_BASE_REGEN
    retryable = status in _RETRYABLE_STATUSES and not base_regeneration

    # Promotion is blocked by the Phase 5 API.  Even if a future caller grants
    # authority, no non-pass state can expose an approval affordance.
    approval_enabled = bool(promotion_authorized and overall_pass)
    actions = {
        "approve": {"visible": approval_enabled, "enabled": approval_enabled},
        "cancel": {"visible": status in {"QUEUED", "RUNNING"}, "enabled": status in {"QUEUED", "RUNNING"}},
        "retry": {
            "visible": retryable,
            "enabled": retryable,
            "requiresNewAttemptId": True,
            "automatic": False,
        },
        "baseRegeneration": {
            "visible": base_regeneration,
            "enabled": base_regeneration,
            "automatic": False,
        },
    }
    return {
        "job": {
            key: public[key]
            for key in ("jobId", "runId", "attemptId", "status", "route", "routeReasons", "error")
            if key in public
        },
        "profileSelector": {
            "options": [{"profileId": profile_id} for profile_id in profile_ids],
            "selectedProfileId": selected,
        },
        "preflight": public.get("preflight", {"status": "UNVALIDATED", "reasons": ["MISSING_PREFLIGHT_EVIDENCE"]}),
        "quality": {
            "overallStatus": quality_status,
            "correctness": correctness,
            "scopes": scopes,
        },
        "actions": actions,
        "baseRegenerationRequired": base_regeneration,
        "automaticRetry": False,
    }


def _validate_value(value: Any, location: str) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise CandidateV3FrontendError("CLIENT_PAYLOAD_KEY_INVALID")
            lowered = key.lower()
            if any(part in lowered for part in _FORBIDDEN_KEY_PARTS):
                raise CandidateV3FrontendError(f"CLIENT_PAYLOAD_UNSAFE_FIELD:{location}.{key}")
            if key.endswith("Id") and (not isinstance(child, str) or not child):
                raise CandidateV3FrontendError(f"CLIENT_PAYLOAD_ID_INVALID:{location}.{key}")
            _validate_value(child, f"{location}.{key}")
        return
    if isinstance(value, (str, bool, int, float)) or value is None:
        if isinstance(value, float) and not math.isfinite(value):
            raise CandidateV3FrontendError(f"CLIENT_PAYLOAD_NUMBER_INVALID:{location}")
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _validate_value(child, f"{location}[{index}]")
        return
    if isinstance(value, (bytes, bytearray, Path)):
        raise CandidateV3FrontendError(f"CLIENT_PAYLOAD_UNSAFE_VALUE:{location}")
    raise CandidateV3FrontendError(f"CLIENT_PAYLOAD_VALUE_INVALID:{location}")


def _safe_scalar(value: Any, key: str) -> Any:
    if isinstance(value, bool) or isinstance(value, int) or isinstance(value, str) or value is None:
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    if key.endswith("Id") and isinstance(value, str) and value:
        return value
    raise CandidateV3FrontendError(f"CLIENT_RESULT_FIELD_INVALID:{key}")


def _safe_text(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _safe_optional_id(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _safe_strings(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [item for item in value if isinstance(item, str)]


def _profile_ids(values: Sequence[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, bytearray)):
        raise CandidateV3FrontendError("PROFILE_IDS_MUST_BE_SEQUENCE")
    normalized = []
    for value in values:
        if not isinstance(value, str) or not value:
            raise CandidateV3FrontendError("PROFILE_ID_INVALID")
        normalized.append(value)
    return tuple(dict.fromkeys(normalized))


def _quality_status(public: Mapping[str, Any]) -> str:
    value = public.get("qualityStatus")
    if value in _STATUSES:
        return value
    quality = public.get("quality")
    if isinstance(quality, Mapping) and quality.get("status") in _STATUSES:
        return str(quality["status"])
    return "UNVALIDATED"


def _ensure_required_scopes(value: Any) -> dict[str, dict[str, Any]]:
    scopes = value if isinstance(value, Mapping) else {}
    return {
        scope: _project_scope(scope, scopes.get(scope))
        for scope in ("FACE_LOCAL", "BOUNDARY", "SCENARIO_GLOBAL")
    }


def _project_scopes(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, Mapping):
        return _ensure_required_scopes({})
    return _ensure_required_scopes(value)


def _project_scope(scope: str, value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {"scope": scope, "status": "UNVALIDATED", "scores": {}, "reasons": ["MISSING_SCOPE_EVIDENCE"]}
    status = value.get("status") if value.get("status") in _STATUSES else "UNVALIDATED"
    raw_scores = value.get("scores", {})
    scores = {}
    if isinstance(raw_scores, Mapping):
        for key, score in raw_scores.items():
            if isinstance(key, str) and isinstance(score, (int, float)) and not isinstance(score, bool) and math.isfinite(float(score)):
                scores[key] = float(score)
    return {
        "scope": scope,
        "status": status,
        "scores": scores,
        "reasons": _safe_strings(value.get("reasons", [])),
    }


def _project_correctness(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {"status": "UNVALIDATED", "reasons": ["MISSING_CORRECTNESS_EVIDENCE"]}
    status = value.get("status") if value.get("status") in _STATUSES else "UNVALIDATED"
    return {
        "status": status,
        "transformValid": bool(value.get("transformValid")),
        "geometryValid": bool(value.get("geometryValid")),
        "maskContainmentValid": bool(value.get("maskContainmentValid")),
        "pixelLockPassed": bool(value.get("pixelLockPassed")),
        "lineageValid": value.get("lineageValid") if isinstance(value.get("lineageValid"), bool) else None,
        "reasons": _safe_strings(value.get("reasons", [])),
    }


def _project_merged_quality(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {"status": "UNVALIDATED", "failedScopes": [], "decisiveReasons": ["MISSING_QUALITY_EVIDENCE"]}
    status = value.get("status") if value.get("status") in _STATUSES else "UNVALIDATED"
    return {
        "status": status,
        "failedScopes": _safe_strings(value.get("failedScopes", [])),
        "decisiveReasons": _safe_strings(value.get("decisiveReasons", [])),
    }


def _project_preflight(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {"status": "UNVALIDATED", "reasons": ["MISSING_PREFLIGHT_EVIDENCE"]}
    status = value.get("status") if isinstance(value.get("status"), str) else "UNVALIDATED"
    return {"status": status, "reasons": _safe_strings(value.get("reasons", []))}
