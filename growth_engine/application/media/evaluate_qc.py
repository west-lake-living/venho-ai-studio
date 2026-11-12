from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
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


VariantQcStatusUpdater = Callable[[UnitOfWork, str, VariantQcStatus], None]


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

        paid_business_key = (
            f"qc:{variant.sha256}:{caption_hash}:{facts.snapshot_hash}:{policy.ruleset_hash}"
        )
        reserved = self._reserve_budget(paid_business_key)
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
            result = self._evaluator.evaluate(variant_view, caption, facts, policy)
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
                if self._variant_qc_status_updater is None:
                    updater = getattr(tx.media, "update_qc_status", None)
                    if not callable(updater):
                        raise QcStatusPersistenceUnavailable(
                            "MediaRepo.update_qc_status is required to persist QC status atomically"
                        )
                    updater(variant.id, _variant_status(decision))
                else:
                    self._variant_qc_status_updater(tx, variant.id, _variant_status(decision))
                tx.qc.save(report)
                if reserved and not tx.budget.settle(
                    paid_business_key,
                    actual_minor=int(self._cost_estimate_minor),
                    settled_at_ms=report.created_at_ms,
                ):
                    raise RuntimeError("QC budget reservation could not be settled")
            return report
        except Exception as error:
            if reserved:
                with self._uow_factory().begin_immediate() as tx:
                    tx.budget.mark_unknown(paid_business_key)
                if isinstance(error, QcPaidCallUnknown):
                    raise
                raise QcPaidCallUnknown(
                    "QC provider call may have completed; the paid call was marked UNKNOWN."
                ) from error
            raise

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
