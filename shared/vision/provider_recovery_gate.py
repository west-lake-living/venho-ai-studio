"""Fail-closed control plane for an authoritative provider recovery hold.

The gate is deliberately independent of provider transport code.  It owns the
human authorization, one-probe budget, provider lock, and the distinction
between provider recovery and quality evaluation.  Callers must still use the
existing provider adapter and evaluator schemas for the probe itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


AUTHORIZATION_ENV = "PROVIDER_RECOVERY_RECHECK_AUTHORIZED"
RESUME_AUTHORIZATION_ENV = "PROVIDER_AUTHORITATIVE_EVALUATION_RESUME_AUTHORIZED"
MAX_RECOVERY_PROBES = 1
APPROVED_PROVIDER = "Gemini"
APPROVED_MODEL = "gemini-flash-latest"


class ProviderHoldState(str, Enum):
    ACTIVE = "ACTIVE"
    RECOVERY_CHECK_AUTHORIZED = "RECOVERY_CHECK_AUTHORIZED"
    RECOVERY_PROBE_IN_PROGRESS = "RECOVERY_PROBE_IN_PROGRESS"
    RECOVERED = "RECOVERED"


class ProviderRecoveryBlocked(RuntimeError):
    """Raised when a provider action is not authorized by the recovery gate."""


@dataclass(frozen=True)
class ProbeAssessment:
    passed: bool
    failed_criteria: tuple[str, ...]
    quality_verdict: str | None = None


RECOVERY_CRITERIA = (
    "request_succeeded",
    "no_503",
    "no_timeout",
    "no_truncation",
    "no_malformed_json",
    "no_unsupported_schema",
    "parsed_without_repair",
    "required_fields_present",
    "dto_schema_valid",
    "raw_response_preserved",
    "raw_response_hash_recorded",
    "lineage_complete",
    "authoritative_response",
)


def _strict_true(value: Any) -> bool:
    """Only the explicit human value TRUE authorizes recovery."""
    return value == "TRUE"


def _criterion_value(evidence: Mapping[str, Any], criterion: str) -> bool:
    aliases = {
        "request_succeeded": ("request_succeeded", "provider_request_succeeded", "http_success"),
        "no_503": ("no_503", "no503", "not_503"),
        "no_timeout": ("no_timeout", "not_timeout"),
        "no_truncation": ("no_truncation", "not_truncated", "not_truncation"),
        "no_malformed_json": ("no_malformed_json", "json_valid", "not_malformed_json"),
        "no_unsupported_schema": ("no_unsupported_schema", "schema_supported"),
        "parsed_without_repair": ("parsed_without_repair", "parse_repair_false", "parseRepairFalse"),
        "required_fields_present": ("required_fields_present", "requiredFieldsPresent"),
        "dto_schema_valid": ("dto_schema_valid", "schema_valid", "dtoValid", "schemaValid"),
        "raw_response_preserved": ("raw_response_preserved", "raw_preserved", "rawPreserved"),
        "raw_response_hash_recorded": ("raw_response_hash_recorded", "raw_hash_recorded", "rawHashRecorded"),
        "lineage_complete": ("lineage_complete", "lineageComplete"),
        "authoritative_response": ("authoritative_response", "authoritativeResponse"),
    }
    return any(evidence.get(alias) is True for alias in aliases[criterion])


def assess_recovery_probe(evidence: Mapping[str, Any]) -> ProbeAssessment:
    """Evaluate the immutable, already-captured probe evidence.

    A quality FAIL is intentionally not a failed recovery criterion.  It is a
    valid provider response as long as every transport, parsing, schema, raw
    evidence, and lineage criterion is true.
    """
    failed = tuple(name for name in RECOVERY_CRITERIA if not _criterion_value(evidence, name))
    verdict = evidence.get("quality_verdict") or evidence.get("qualityVerdict")
    return ProbeAssessment(not failed, failed, str(verdict) if verdict is not None else None)


class ProviderRecoveryGate:
    """Explicit state machine for provider-hold recovery."""

    def __init__(
        self,
        hold_document: Mapping[str, Any],
        *,
        environment: Mapping[str, str] | None = None,
        provider: str = APPROVED_PROVIDER,
        model: str = APPROVED_MODEL,
    ) -> None:
        self.environment = environment if environment is not None else {}
        hold = hold_document.get("provider_hold")
        if not isinstance(hold, Mapping):
            raise ProviderRecoveryBlocked("PROVIDER_HOLD_STATE_INVALID")
        self.provider = provider
        self.model = model
        self._hold_document = dict(hold_document)
        self._probe_count = 0
        self._transitions: list[dict[str, str]] = []
        if hold.get("active") is True:
            self.state = ProviderHoldState.ACTIVE
        elif hold.get("active") is False:
            self.state = ProviderHoldState.RECOVERED
        else:
            raise ProviderRecoveryBlocked("PROVIDER_HOLD_STATE_INVALID")

    @property
    def probe_count(self) -> int:
        return self._probe_count

    @property
    def transitions(self) -> tuple[dict[str, str], ...]:
        return tuple(self._transitions)

    @property
    def authorization_raw(self) -> str | None:
        return self.environment.get(AUTHORIZATION_ENV)

    def _transition(self, state: ProviderHoldState, reason: str) -> None:
        previous = self.state
        self.state = state
        self._transitions.append({"from": previous.value, "to": state.value, "reason": reason})

    def authorize_recovery(self) -> None:
        if self.state != ProviderHoldState.ACTIVE:
            raise ProviderRecoveryBlocked(f"RECOVERY_NOT_AVAILABLE_IN_STATE:{self.state.value}")
        if not _strict_true(self.authorization_raw):
            raise ProviderRecoveryBlocked(
                "PROVIDER_HOLD_ACTIVE: explicit PROVIDER_RECOVERY_RECHECK_AUTHORIZED=TRUE is required"
            )
        self._transition(ProviderHoldState.RECOVERY_CHECK_AUTHORIZED, "explicit_human_authorization")

    def begin_recovery_probe(self) -> None:
        if self.state == ProviderHoldState.ACTIVE:
            self.authorize_recovery()
        if self.state != ProviderHoldState.RECOVERY_CHECK_AUTHORIZED:
            raise ProviderRecoveryBlocked(f"RECOVERY_PROBE_BLOCKED_IN_STATE:{self.state.value}")
        if self._probe_count >= MAX_RECOVERY_PROBES:
            raise ProviderRecoveryBlocked("RECOVERY_PROBE_BUDGET_EXHAUSTED:1/1")
        self._probe_count += 1
        self._transition(ProviderHoldState.RECOVERY_PROBE_IN_PROGRESS, "single_minimal_probe_started")

    def complete_recovery_probe(self, evidence: Mapping[str, Any]) -> ProbeAssessment:
        if self.state != ProviderHoldState.RECOVERY_PROBE_IN_PROGRESS:
            raise ProviderRecoveryBlocked("RECOVERY_PROBE_NOT_IN_PROGRESS")
        assessment = assess_recovery_probe(evidence)
        self._transition(
            ProviderHoldState.RECOVERED if assessment.passed else ProviderHoldState.ACTIVE,
            "all_recovery_criteria_passed" if assessment.passed else "recovery_criteria_not_proven",
        )
        return assessment

    def assert_provider_lock(self, provider: str, model: str) -> None:
        if provider.casefold() != self.provider.casefold() or model != self.model:
            raise ProviderRecoveryBlocked(
                f"PROVIDER_LOCK_MISMATCH: expected {self.provider}/{self.model}, got {provider}/{model}"
            )

    def assert_bulk_evaluation_blocked(self, lane: str) -> None:
        """R1-P5 never starts pending quality evaluation, including after PASS."""
        raise ProviderRecoveryBlocked(
            f"BULK_EVALUATION_BLOCKED_BY_R1_P5:{lane}:separate_authoritative_resume_task_required"
        )

    def assert_bulk_evaluation_authorized(self, lane: str) -> None:
        """Optional future-task guard: recovery alone never grants bulk access."""
        if self.state != ProviderHoldState.RECOVERED or not _strict_true(self.environment.get(RESUME_AUTHORIZATION_ENV)):
            raise ProviderRecoveryBlocked(
                f"BULK_EVALUATION_BLOCKED:{lane}:hold={self.state.value};separate_authorization_required"
            )

    def snapshot(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "provider": self.provider,
            "model": self.model,
            "authorization": {
                "name": AUTHORIZATION_ENV,
                "rawValuePresent": self.authorization_raw is not None,
                "accepted": _strict_true(self.authorization_raw),
            },
            "probeCount": self._probe_count,
            "maxRecoveryProbes": MAX_RECOVERY_PROBES,
            "transitions": list(self._transitions),
            "bulkEvaluation": "BLOCKED_IN_R1_P5",
            "pendingAuthoritativeEvaluations": 18,
        }
