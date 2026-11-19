from __future__ import annotations

import hashlib
import inspect
import json
import math
import re
import tempfile
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from pathlib import Path
from typing import Any, Callable

from growth_engine.application.dto import EffectiveQcPolicy, FactSnapshot, QcResult, VariantView
from growth_engine.application.ports.media import MediaStore
from knowledge_studio.vision.schemas.base import BaseDNA
from validator_studio.image_validator import report_from_image_observations, validate_image
from validator_studio.observe_adapter import parse_image_observation_response
from validator_studio.utils import find_dna_path

_IDENTIFIER = re.compile(r"^[a-z0-9_]+$")
_MAX_VARIANT_BYTES = 5 * 1024 * 1024
_UNVERIFIED_RAILING_TERMS = ("railing", "railings", "balustrade", "lan can", "lan-can")


class UnsupportedQcConfigurationError(ValueError):
    pass


class QcArtifactError(ValueError):
    pass


class QcNonFiniteNumberError(ValueError):
    code = "ERR_GC2_QC_NONFINITE_NUMBER"


class LegacyQcAdapter:
    """Adapter around Validator Studio's DNA and image scoring contract."""

    def __init__(
        self,
        media_store: MediaStore,
        *,
        base_dir: Path | None = None,
        validator_fn: Callable[..., Any] | None = None,
        provider: str = "mock",
    ) -> None:
        self._media_store = media_store
        self._base_dir = (base_dir or Path(__file__).resolve().parents[4]).resolve()
        self._validator_fn = validator_fn or validate_image
        self._provider = provider

    def compile_policy(self, project: str, subject: str, scenario: str | None) -> EffectiveQcPolicy:
        return compile_effective_qc_policy(project, subject, scenario, base_dir=self._base_dir)

    def evaluate(
        self,
        variant: VariantView,
        caption: str,
        facts: FactSnapshot,
        policy: EffectiveQcPolicy,
        response_sink: Callable[[dict[str, Any]], None] | None = None,
    ) -> QcResult:
        image_bytes = self._read_verified_variant(variant)

        with tempfile.TemporaryDirectory(prefix="growth-qc-") as temp_dir:
            image_path = Path(temp_dir) / "approved-variant.jpg"
            image_path.write_bytes(image_bytes)
            validator_arguments: dict[str, Any] = {
                "provider": self._provider,
                "scenario_profile_id": None,
            }
            if response_sink is not None:
                if _supports_keyword(self._validator_fn, "raw_response_sink"):
                    validator_arguments["raw_response_sink"] = lambda event: response_sink({
                        "source": "validator",
                        "event": event,
                    })
                if _supports_keyword(self._validator_fn, "transport_event_sink"):
                    validator_arguments["transport_event_sink"] = lambda event: response_sink({
                        "source": "provider",
                        "event": event,
                    })
            report = self._validator_fn(
                policy.project,
                policy.subject,
                image_path,
                **validator_arguments,
            )

        return self._result_from_report(report, variant, caption, facts, policy)

    def reprocess_response(
        self,
        variant: VariantView,
        caption: str,
        facts: FactSnapshot,
        policy: EffectiveQcPolicy,
        response: object,
    ) -> QcResult:
        """Rebuild QC locally from a previously captured response; never calls a provider."""
        image_bytes = self._read_verified_variant(variant)
        with tempfile.TemporaryDirectory(prefix="growth-qc-reprocess-") as temp_dir:
            image_path = Path(temp_dir) / "approved-variant.jpg"
            image_path.write_bytes(image_bytes)
            observation = parse_image_observation_response(response)
            report = report_from_image_observations(
                policy.project,
                policy.subject,
                image_path,
                [observation],
                provider=self._provider,
            )
        return self._result_from_report(report, variant, caption, facts, policy)

    def _read_verified_variant(self, variant: VariantView) -> bytes:
        if variant.mime != "image/jpeg" or variant.qc_status == "QUARANTINED":
            raise QcArtifactError("variant must be a non-quarantined JPEG")
        with self._media_store.open(variant.object_key) as source:
            image_bytes = source.read(_MAX_VARIANT_BYTES + 1)
        if len(image_bytes) > _MAX_VARIANT_BYTES:
            raise QcArtifactError("variant exceeds QC size limit")
        if hashlib.sha256(image_bytes).hexdigest() != variant.sha256:
            raise QcArtifactError("variant bytes do not match SHA-256 metadata")
        return image_bytes

    def _result_from_report(
        self,
        report: Any,
        variant: VariantView,
        caption: str,
        facts: FactSnapshot,
        policy: EffectiveQcPolicy,
    ) -> QcResult:
        reported_sha = getattr(getattr(report, "artifact_ref", None), "hash", None)
        if reported_sha not in {variant.sha256, f"sha256:{variant.sha256}"}:
            raise QcArtifactError("Validator Studio report references different image bytes")

        violations = [
            item for item in getattr(report, "forbidden_violations", ())
            if _field(item, "violated") is True
            and _field(item, "source", "curated") == "curated"
            and _field(item, "rule") in policy.forbidden
        ]
        coverage_gaps = ["technical_quality_detector_unverified"]
        if any(_contains_term(rule, _UNVERIFIED_RAILING_TERMS) for rule in policy.forbidden):
            coverage_gaps.append("railing_presence_detector_unverified")
        if violations:
            coverage_gaps.extend(f"forbidden_violated:{_field(item, 'rule')}" for item in violations)

        verdict = _field(getattr(report, "verdict", None), "value", _field(report, "verdict", "reject"))
        kill_switch = getattr(report, "kill_switch", None)
        kill_switch_triggered = _field(kill_switch, "triggered", False) is True
        if violations or kill_switch_triggered:
            decision = "FAIL"
        elif coverage_gaps:
            decision = "REVIEW"
        elif verdict == "approve":
            decision = "PASS"
        elif verdict == "reject":
            decision = "FAIL"
        else:
            decision = "REVIEW"

        report_json = report.model_dump(mode="json")
        result_payload = {
            "validator_report": report_json,
            "effective_forbidden": list(policy.forbidden),
            "kill_switch_triggered": kill_switch_triggered,
            "forbidden_violations": [
                {"rule": _field(item, "rule"), "source": _field(item, "source", "curated"), "violated": True}
                for item in violations
            ],
            "coverage_gaps": coverage_gaps,
        }
        result_payload = _normalize_qc_numbers(result_payload)
        return QcResult(
            decision=decision,
            ruleset_hash=policy.ruleset_hash,
            caption_hash=hashlib.sha256(caption.encode("utf-8")).hexdigest(),
            fact_snapshot_hash=facts.snapshot_hash,
            coverage_gaps=tuple(dict.fromkeys(coverage_gaps)),
            result_json=json.dumps(result_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        )


def _normalize_qc_numbers(value: Any, path: str = "$", *, unit_declared: bool = False) -> Any:
    """Encode every QC float as deterministic integer basis points for canonical storage."""
    if isinstance(value, float):
        if not math.isfinite(value):
            raise QcNonFiniteNumberError(
                f"field {path}: QC number must be finite; NaN and infinity are not allowed"
            )
        try:
            decimal = Decimal(str(value))
        except (InvalidOperation, ValueError):
            raise ValueError(f"field {path}: QC number cannot be represented as Decimal") from None
        return int((decimal * Decimal(10_000)).to_integral_value(rounding=ROUND_HALF_EVEN))
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, nested in value.items():
            target_key = key
            declares_unit = key == "category_scores" and _contains_float(nested)
            if declares_unit:
                target_key = "category_scores_bp"
            elif not unit_declared and isinstance(nested, (list, tuple)) and any(
                isinstance(item, float) for item in nested
            ):
                target_key = _with_bp_unit(key)
            elif not unit_declared and isinstance(nested, float):
                target_key = _with_bp_unit(key)
            normalized[target_key] = _normalize_qc_numbers(
                nested,
                f"{path}.{target_key}",
                unit_declared=unit_declared or declares_unit,
            )
        return normalized
    if isinstance(value, (list, tuple)):
        return [
            _normalize_qc_numbers(item, f"{path}[{index}]", unit_declared=unit_declared)
            for index, item in enumerate(value)
        ]
    return value


def _contains_float(value: Any) -> bool:
    if isinstance(value, float):
        return True
    if isinstance(value, dict):
        return any(_contains_float(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_float(item) for item in value)
    return False


def _with_bp_unit(key: str) -> str:
    return key if key.endswith("_bp") else f"{key}_bp"


def compile_effective_qc_policy(
    project: str,
    subject: str,
    scenario: str | None,
    *,
    base_dir: Path | None = None,
) -> EffectiveQcPolicy:
    """Compile the one supported effective policy from DNA JSON + reference config."""
    if not _IDENTIFIER.fullmatch(project) or not _IDENTIFIER.fullmatch(subject):
        raise UnsupportedQcConfigurationError("project and subject must be stable identifiers")
    if scenario is not None:
        raise UnsupportedQcConfigurationError(
            "scenario QC overlays are unsupported; Growth rules must be curated in DNA JSON"
        )
    root = (base_dir or Path(__file__).resolve().parents[4]).resolve()
    dna_path = find_dna_path(project, subject, base_dir=root)
    dna_bytes = dna_path.read_bytes()
    try:
        dna = BaseDNA.model_validate(json.loads(dna_bytes))
    except (json.JSONDecodeError, ValueError) as exc:
        raise UnsupportedQcConfigurationError("subject DNA JSON is invalid") from exc
    if dna.subject.casefold() != subject.casefold():
        raise UnsupportedQcConfigurationError("subject DNA does not match requested subject")

    reference_path = root / "config" / "validation.yaml"
    try:
        reference_bytes = reference_path.read_bytes()
    except OSError as exc:
        raise UnsupportedQcConfigurationError("Validator reference config is missing") from exc
    forbidden = tuple(rule.rule for rule in dna.forbidden if rule.source == "curated")
    ruleset_payload = {
        "project": project,
        "subject": subject,
        "scenario": None,
        "dna_sha256": hashlib.sha256(dna_bytes).hexdigest(),
        "dna_contract_version": dna.contract_version,
        "dna_version": dna.dna_version,
        "reference_config_sha256": hashlib.sha256(reference_bytes).hexdigest(),
        "forbidden": list(forbidden),
    }
    ruleset_hash = hashlib.sha256(
        json.dumps(ruleset_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return EffectiveQcPolicy(project, subject, None, ruleset_hash, forbidden)


def _field(value: object, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _supports_keyword(function: Callable[..., Any], keyword: str) -> bool:
    try:
        parameters = inspect.signature(function).parameters.values()
    except (TypeError, ValueError):
        return False
    return any(
        parameter.name == keyword or parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in parameters
    )


def _contains_term(text: str, terms: tuple[str, ...]) -> bool:
    normalized = text.casefold().replace("đ", "d")
    return any(term in normalized for term in terms)
