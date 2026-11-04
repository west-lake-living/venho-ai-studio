from __future__ import annotations

import hashlib
import json
import re
import tempfile
from pathlib import Path
from typing import Any, Callable

from growth_engine.application.dto import EffectiveQcPolicy, FactSnapshot, QcResult, VariantView
from growth_engine.application.ports.media import MediaStore
from knowledge_studio.vision.schemas.base import BaseDNA
from validator_studio.image_validator import validate_image
from validator_studio.utils import find_dna_path

_IDENTIFIER = re.compile(r"^[a-z0-9_]+$")
_MAX_VARIANT_BYTES = 5 * 1024 * 1024
_UNVERIFIED_RAILING_TERMS = ("railing", "railings", "balustrade", "lan can", "lan-can")


class UnsupportedQcConfigurationError(ValueError):
    pass


class QcArtifactError(ValueError):
    pass


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
    ) -> QcResult:
        if variant.mime != "image/jpeg" or variant.qc_status == "QUARANTINED":
            raise QcArtifactError("variant must be a non-quarantined JPEG")
        with self._media_store.open(variant.object_key) as source:
            image_bytes = source.read(_MAX_VARIANT_BYTES + 1)
        if len(image_bytes) > _MAX_VARIANT_BYTES:
            raise QcArtifactError("variant exceeds QC size limit")
        artifact_sha256 = hashlib.sha256(image_bytes).hexdigest()
        if artifact_sha256 != variant.sha256:
            raise QcArtifactError("variant bytes do not match SHA-256 metadata")

        with tempfile.TemporaryDirectory(prefix="growth-qc-") as temp_dir:
            image_path = Path(temp_dir) / "approved-variant.jpg"
            image_path.write_bytes(image_bytes)
            report = self._validator_fn(
                policy.project,
                policy.subject,
                image_path,
                provider=self._provider,
                scenario_profile_id=None,
            )

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
        return QcResult(
            decision=decision,
            ruleset_hash=policy.ruleset_hash,
            caption_hash=hashlib.sha256(caption.encode("utf-8")).hexdigest(),
            fact_snapshot_hash=facts.snapshot_hash,
            coverage_gaps=tuple(dict.fromkeys(coverage_gaps)),
            result_json=json.dumps(result_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        )


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


def _contains_term(text: str, terms: tuple[str, ...]) -> bool:
    normalized = text.casefold().replace("đ", "d")
    return any(term in normalized for term in terms)
