from __future__ import annotations

import hashlib
import inspect
import json
import re
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from growth_engine.application.dto import EffectiveQcPolicy, FactSnapshot, VariantView
from growth_engine.application.errors import NotFound
from growth_engine.application.ports.clock import Clock, IdGenerator
from growth_engine.application.ports.content import QcEvaluator
from growth_engine.application.ports.uow import UnitOfWork
from growth_engine.domain.media.asset import VariantQcStatus
from growth_engine.domain.media.qc import QcDecision, QcReport
from growth_engine.domain.delivery.revision import normalize_caption


class QcStatusPersistenceUnavailable(RuntimeError):
    pass


class QcPaidCallUnknown(RuntimeError):
    """A QC provider call may have completed; it must not be retried automatically."""


class QcPostResponseError(RuntimeError):
    code = "ERR_GC2_QC_POST_RESPONSE_FAILED"

    def __init__(self, error: Exception) -> None:
        error_type = type(error).__name__
        error_code = getattr(error, "code", None)
        detail = _safe_postprocess_detail(error)
        self.public_message = (
            "QC provider response was received and cost settled, but post-response processing failed "
            f"(error_type={error_type}, error_code={error_code or 'UNCLASSIFIED'}, detail={detail}); "
            "filtered response evidence was retained."
        )
        super().__init__(self.public_message)


VariantQcStatusUpdater = Callable[[UnitOfWork, str, VariantQcStatus], None]
_SECRET_KEY = re.compile(
    r"(?i)(authorization|bearer|access[_-]?token|refresh[_-]?token|api[_-]?key|client[_-]?secret|password|secret|(?:^|_)token(?:$|_))"
)
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(authorization|bearer|access[_-]?token|refresh[_-]?token|api[_-]?key|client[_-]?secret|password|token)"
    r"(\s*[:=]\s*|\s+)([^\s,;]+)"
)
_JSON_SECRET_ASSIGNMENT = re.compile(
    r"(?i)([\"']?(?:authorization|bearer|access[_-]?token|refresh[_-]?token|api[_-]?key|client[_-]?secret|password|token)[\"']?\s*:\s*[\"']?)"
    r"([^\"'\s,;}{]+)"
)
_URL = re.compile(r"https?://[^\s\])}>,]+", re.IGNORECASE)
_LONG_SECRET = re.compile(r"\b[A-Za-z0-9_-]{48,}\b")
_MAX_EVIDENCE_TEXT = 32_768


class EvaluateQc:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        evaluator: QcEvaluator,
        clock: Clock,
        ids: IdGenerator,
        *,
        variant_qc_status_updater: VariantQcStatusUpdater | None = None,
        budget_policy: object | None = None,
        cost_estimate_minor: int | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._evaluator = evaluator
        self._clock = clock
        self._ids = ids
        self._variant_qc_status_updater = variant_qc_status_updater
        self._budget_policy = budget_policy
        self._cost_estimate_minor = cost_estimate_minor
        if budget_policy is not None:
            cap = getattr(budget_policy, "monthly_cap_minor", None)
            currency = getattr(budget_policy, "currency", None)
            if type(cap) is not int or cap <= 0 or not isinstance(currency, str) or not currency.strip():
                raise ValueError("QC budget policy is invalid")
            if type(cost_estimate_minor) is not int or cost_estimate_minor <= 0:
                raise ValueError("a positive QC cost estimate is required when QC budget is enabled")

    def execute(
        self,
        *,
        variant_id: str,
        caption: str,
        facts: FactSnapshot,
        project: str,
        subject: str,
        scenario: str | None = None,
        qc_retry_key: str | None = None,
    ) -> QcReport:
        with self._uow_factory().read_only() as tx:
            variant = tx.media.get_variant(variant_id)
        if variant is None:
            raise NotFound("Không tìm thấy biến thể ảnh.")

        policy: EffectiveQcPolicy = self._evaluator.compile_policy(project, subject, scenario)
        caption = normalize_caption(caption)
        caption_hash = hashlib.sha256(caption.encode("utf-8")).hexdigest()
        existing = self._find_report(
            variant.id, caption_hash, facts.snapshot_hash, policy.ruleset_hash
        )
        if existing is not None:
            return existing

        shared_report = self._reuse_matching_image_report(
            variant.id, variant.sha256, caption_hash, facts.snapshot_hash, policy.ruleset_hash,
        )
        if shared_report is not None:
            return shared_report

        retry_key = qc_retry_key
        if retry_key is not None and (not retry_key.strip() or len(retry_key) > 128):
            raise ValueError("QC retry key is invalid")
        paid_business_key = f"qc:{variant.sha256}:{caption_hash}:{facts.snapshot_hash}:{policy.ruleset_hash}"
        if retry_key:
            paid_business_key += f":retry:{retry_key}"
        reserved = self._reserve_budget(paid_business_key)
        provider_response_received = False
        evidence_events: list[dict[str, object]] = []

        def record_evidence(event: dict[str, object]) -> None:
            nonlocal provider_response_received
            safe_event = _safe_evidence_value(event)
            if not isinstance(safe_event, dict):
                safe_event = {"event": "invalid_evidence_shape"}
            evidence_events.append(safe_event)
            inner = event.get("event")
            source = event.get("source")
            if source == "provider" and isinstance(inner, dict) and inner.get("event") == "response_received":
                provider_response_received = True
            if source == "validator" and isinstance(inner, dict) and "rawResponse" in inner:
                provider_response_received = True
            if reserved:
                self._persist_provider_evidence(
                    paid_business_key,
                    evidence_events,
                    settle=provider_response_received,
                )

        try:
            variant_view = VariantView(
                variant_id=variant.id,
                sha256=variant.sha256,
                width=variant.width,
                height=variant.height,
                mime=variant.mime,
                object_key=variant.object_key,
                qc_status=variant.qc_status.value,
            )
            try:
                evaluate_parameters = inspect.signature(self._evaluator.evaluate).parameters
            except (TypeError, ValueError):
                evaluate_parameters = {}
            if "response_sink" in evaluate_parameters or any(
                parameter.kind is inspect.Parameter.VAR_KEYWORD
                for parameter in evaluate_parameters.values()
            ):
                result = self._evaluator.evaluate(
                    variant_view, caption, facts, policy, response_sink=record_evidence
                )
            else:
                result = self._evaluator.evaluate(variant_view, caption, facts, policy)
            # A returned QC result proves that a provider response was received, even for
            # legacy evaluator implementations which do not expose the response callback.
            if reserved:
                # In production the budget ledger is enabled and a successful evaluator
                # return without transport hooks is still evidence that the paid result
                # arrived. Non-paid/test evaluators do not imply an external call.
                provider_response_received = True
            evidence_events.append(_safe_evidence_value({
                "stage": "qc_result_returned",
                "decision": result.decision,
                "result_json": result.result_json,
            }))
            if reserved:
                self._persist_provider_evidence(paid_business_key, evidence_events, settle=True)
            if (
                result.ruleset_hash != policy.ruleset_hash
                or result.caption_hash != caption_hash
                or result.fact_snapshot_hash != facts.snapshot_hash
            ):
                raise ValueError("QC result does not match the active policy, caption, or fact snapshot")

            decision = _effective_decision(result.decision, result.result_json, policy.forbidden, result.coverage_gaps)
            report = QcReport(
                id=self._ids.new_id(),
                variant_id=variant.id,
                caption_hash=caption_hash,
                ruleset_hash=policy.ruleset_hash,
                fact_snapshot_hash=facts.snapshot_hash,
                decision=decision,
                coverage_gaps=tuple(dict.fromkeys(result.coverage_gaps)),
                result_json=result.result_json,
                created_at_ms=self._clock.now_ms(),
            )
            with self._uow_factory().begin_immediate() as tx:
                current_variant = tx.media.get_variant(variant.id)
                if current_variant is None or current_variant.sha256 != variant.sha256:
                    raise ValueError("media variant changed during QC")
                self._update_variant_qc_status(tx, report)
                tx.qc.save(report)
                if reserved:
                    paid_call = tx.budget.get(paid_business_key)
                    if paid_call is not None and paid_call["state"] == "RESERVED":
                        if not tx.budget.settle(
                            paid_business_key,
                            actual_minor=int(self._cost_estimate_minor),
                            settled_at_ms=report.created_at_ms,
                        ):
                            raise RuntimeError("QC budget reservation could not be settled")
            return report
        except Exception as error:
            if provider_response_received:
                if reserved:
                    evidence_events.append({
                        "stage": "postprocess_error",
                        "code": QcPostResponseError.code,
                        "error_type": type(error).__name__,
                        "detail": _safe_postprocess_detail(error),
                    })
                    self._persist_provider_evidence(paid_business_key, evidence_events, settle=True)
                if isinstance(error, QcPostResponseError):
                    raise
                raise QcPostResponseError(error) from None
            if reserved:
                with self._uow_factory().begin_immediate() as tx:
                    tx.budget.mark_unknown(paid_business_key)
                if isinstance(error, QcPaidCallUnknown):
                    raise
                raise QcPaidCallUnknown(
                    "QC provider call may have completed; the paid call was marked UNKNOWN."
                ) from error
            raise

    def _reuse_matching_image_report(
        self, variant_id: str, sha256: str, caption_hash: str, fact_hash: str, ruleset_hash: str,
    ) -> QcReport | None:
        with self._uow_factory().begin_immediate() as tx:
            finder = getattr(tx.qc, "find_matching_image", None)
            if not callable(finder):
                return None
            if existing := tx.qc.find_matching(variant_id, caption_hash, fact_hash, ruleset_hash):
                return existing
            if (equivalent := finder(sha256, caption_hash, fact_hash, ruleset_hash)) is None:
                return None
            variant = tx.media.get_variant(variant_id)
            if variant is None or variant.sha256 != sha256:
                raise ValueError("media variant changed during QC reuse")
            # Receipt and approval still bind to this variant's own report.
            report = replace(equivalent, id=self._ids.new_id(), variant_id=variant_id,
                             created_at_ms=self._clock.now_ms())
            self._update_variant_qc_status(tx, report)
            tx.qc.save(report)
            return report

    def _update_variant_qc_status(self, tx: UnitOfWork, report: QcReport) -> None:
        status = _variant_status(report.decision)
        if self._variant_qc_status_updater is not None:
            self._variant_qc_status_updater(tx, report.variant_id, status)
            return
        updater = getattr(tx.media, "update_qc_status", None)
        if not callable(updater):
            raise QcStatusPersistenceUnavailable(
                "MediaRepo.update_qc_status is required to persist QC status atomically"
            )
        updater(report.variant_id, status)

    def _persist_provider_evidence(
        self,
        business_key: str,
        events: list[dict[str, object]],
        *,
        settle: bool,
    ) -> None:
        payload = json.dumps(events, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        now_ms = self._clock.now_ms()
        with self._uow_factory().begin_immediate() as tx:
            if not tx.budget.record_provider_response(business_key, response_json=payload):
                raise RuntimeError("QC provider evidence could not be persisted")
            paid_call = tx.budget.get(business_key)
            if settle and paid_call is not None and paid_call["state"] == "RESERVED":
                if not tx.budget.settle(
                    business_key,
                    actual_minor=int(self._cost_estimate_minor),
                    settled_at_ms=now_ms,
                ):
                    raise RuntimeError("confirmed QC provider cost could not be settled")

    def _find_report(
        self,
        variant_id: str,
        caption_hash: str,
        fact_snapshot_hash: str,
        ruleset_hash: str,
    ) -> QcReport | None:
        with self._uow_factory().read_only() as tx:
            finder = getattr(tx.qc, "find_matching", None)
            return (
                finder(variant_id, caption_hash, fact_snapshot_hash, ruleset_hash)
                if callable(finder)
                else None
            )

    def _reserve_budget(self, business_key: str) -> bool:
        if self._budget_policy is None:
            return False
        now_ms = self._clock.now_ms()
        period_key = datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc).astimezone(
            ZoneInfo("Asia/Ho_Chi_Minh")
        ).strftime("%Y-%m")
        with self._uow_factory().begin_immediate() as tx:
            accepted = tx.budget.reserve(
                call_id=self._ids.new_id(),
                business_key=business_key,
                period_key=period_key,
                currency=str(getattr(self._budget_policy, "currency")),
                provider="legacy_openai_vision",
                operation="image_qc",
                amount_minor=int(self._cost_estimate_minor),
                cap_minor=int(getattr(self._budget_policy, "monthly_cap_minor")),
                created_at_ms=now_ms,
            )
            if accepted:
                return True
            existing = tx.budget.get(business_key)
            if existing is not None:
                raise QcPaidCallUnknown("QC cost reservation exists without a matching persisted report.")
            raise ValueError("v2 monthly budget does not have enough remaining allowance for image QC")


def evaluate_qc(use_case: EvaluateQc, **arguments: object) -> QcReport:
    return use_case.execute(**arguments)  # type: ignore[arg-type]


def _effective_decision(
    raw_decision: str,
    result_json: str,
    forbidden: tuple[str, ...],
    coverage_gaps: tuple[str, ...],
) -> QcDecision:
    try:
        decision = QcDecision(raw_decision.upper())
    except (AttributeError, ValueError) as exc:
        raise ValueError("QC evaluator returned an invalid decision") from exc
    try:
        payload = json.loads(result_json)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("QC evaluator returned invalid JSON") from exc
    violations = payload.get("forbidden_violations", []) if isinstance(payload, dict) else []
    hard_violation = any(
        isinstance(item, dict)
        and item.get("violated") is True
        and item.get("rule") in forbidden
        and item.get("source", "curated") == "curated"
        for item in violations
    )
    kill_switch = payload.get("kill_switch_triggered", False) if isinstance(payload, dict) else False
    if hard_violation or kill_switch:
        return QcDecision.FAIL
    if decision is QcDecision.PASS and coverage_gaps:
        return QcDecision.REVIEW
    return decision


def _variant_status(decision: QcDecision) -> VariantQcStatus:
    return {
        QcDecision.PASS: VariantQcStatus.PASS,
        QcDecision.FAIL: VariantQcStatus.FAIL,
        QcDecision.REVIEW: VariantQcStatus.REVIEW,
    }[decision]


def _safe_evidence_value(value: object, *, key: str = "") -> object:
    if _SECRET_KEY.search(key):
        return "[REDACTED]"
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            decoded = None
        if isinstance(decoded, (dict, list)):
            return _safe_evidence_value(decoded, key=key)
        safe = _JSON_SECRET_ASSIGNMENT.sub(r"\1[REDACTED]", value)
        safe = _SECRET_ASSIGNMENT.sub(r"\1\2[REDACTED]", safe)
        safe = _URL.sub("[URL REDACTED]", safe)
        safe = _LONG_SECRET.sub("[SECRET REDACTED]", safe)
        safe = " ".join(safe.split())
        if len(safe) > _MAX_EVIDENCE_TEXT:
            safe = safe[:_MAX_EVIDENCE_TEXT] + " [TRUNCATED]"
        return safe
    if isinstance(value, dict):
        return {str(name): _safe_evidence_value(item, key=str(name)) for name, item in value.items() if name != "parseError"}
    if isinstance(value, (list, tuple)):
        return [_safe_evidence_value(item) for item in value[:500]]
    if value is None or type(value) in {bool, int, float}:
        return value
    return type(value).__name__


def _safe_postprocess_detail(error: Exception) -> str:
    errors_method = getattr(error, "errors", None)
    if callable(errors_method):
        try:
            details = errors_method(include_input=False)[:4]
            message = "; ".join(
                f"{'.'.join(str(part) for part in item.get('loc', ())) or '$'}: {item.get('msg', 'invalid value')}"
                for item in details
            )
        except (TypeError, ValueError):
            message = type(error).__name__
    else:
        message = str(error) or type(error).__name__
        safe_prefixes = (
            "field ",
            "image observation schema invalid",
            "Weight categories mismatch.",
            "Weight total must be",
            "QC evaluator returned",
            "QC result does not match",
            "media variant changed during QC",
        )
        if not message.startswith(safe_prefixes):
            message = type(error).__name__
    safe = _SECRET_ASSIGNMENT.sub(r"\1\2[REDACTED]", message)
    safe = _URL.sub("[URL REDACTED]", safe)
    safe = _LONG_SECRET.sub("[SECRET REDACTED]", safe)
    return " ".join(safe.split())[:200] or type(error).__name__
