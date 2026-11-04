from __future__ import annotations

from collections.abc import Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass, replace
from typing import Protocol

from growth_engine.application.ports.clock import Clock, IdGenerator
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.states import DeliveryEvent, DeliveryState
from growth_engine.domain.kernel.errors import DomainError, ErrorCode
from growth_engine.domain.publishing.execution import Execution, ExecutionState
from growth_engine.domain.publishing.receipt import Receipt, ReceiptOutcome, is_placeholder_post_id
from growth_engine.application.publishing.receive_receipt import ReceiptInboxRecord


@dataclass(frozen=True)
class ReceiptApplySnapshot:
    record: ReceiptInboxRecord
    execution: Execution | None
    delivery: Delivery | None
    command_id: str
    revision_id: str
    channel_id: str
    remote_page_id: str
    payload_hash: str
    principal_id: str


@dataclass(frozen=True)
class ApplyReceiptResult:
    processing_state: str
    reason: str | None = None
    delivery_state: str | None = None
    execution_state: str | None = None


class ErrorClassPolicy(Protocol):
    def retryable_for(self, error_class: str) -> bool | None: ...


class ReceiptApplyTransaction(Protocol):
    def load_for_apply(self, receipt_id: str) -> ReceiptApplySnapshot | None: ...

    def commit_apply(
        self,
        snapshot: ReceiptApplySnapshot,
        *,
        execution: Execution | None,
        delivery: Delivery | None,
        processing_state: str,
        reason: str | None,
        verify_at_ms: int | None,
        incident: dict[str, object] | None,
        audit_id: str,
        correlation_id: str,
        at_ms: int,
    ) -> bool: ...


class ReceiptApplyStore(Protocol):
    def begin_immediate(self) -> AbstractContextManager[ReceiptApplyTransaction]: ...


class ApplyReceipt:
    """Apply one durable receipt without treating Make's report as verification."""

    def __init__(
        self,
        store: ReceiptApplyStore,
        clock: Clock,
        ids: IdGenerator,
        error_classes: ErrorClassPolicy,
    ) -> None:
        self._store = store
        self._clock = clock
        self._ids = ids
        self._error_classes = error_classes

    def execute(self, receipt_id: str, *, correlation_id: str) -> ApplyReceiptResult:
        if not receipt_id.strip() or not correlation_id.strip():
            raise DomainError(ErrorCode.VALIDATION, "Yêu cầu áp receipt không hợp lệ.")
        now_ms = self._clock.now_ms()
        with self._store.begin_immediate() as tx:
            snapshot = tx.load_for_apply(receipt_id)
            if snapshot is None:
                raise DomainError(ErrorCode.NOT_FOUND, "Không tìm thấy receipt.")
            record = snapshot.record
            state = getattr(record, "processing_state", None)
            if state != "RECEIVED":
                return ApplyReceiptResult(
                    processing_state=state if isinstance(state, str) else "QUARANTINED",
                    reason=getattr(record, "quarantine_reason", None),
                    delivery_state=_delivery_state(snapshot.delivery),
                    execution_state=_execution_state(snapshot.execution),
                )

            body = getattr(record, "body", None)
            if not isinstance(body, Mapping):
                return self._commit_quarantine(
                    tx,
                    snapshot,
                    reason="INVALID_RECEIPT_BODY",
                    incident_type="RECEIPT_QUARANTINED",
                    details={"receipt_id": receipt_id},
                    correlation_id=correlation_id,
                    now_ms=now_ms,
                )

            mismatches = _identity_mismatches(snapshot, body)
            if mismatches:
                return self._commit_quarantine(
                    tx,
                    snapshot,
                    reason="RECEIPT_IDENTITY_MISMATCH",
                    incident_type="RECEIPT_QUARANTINED",
                    details={
                        "receipt_id": receipt_id,
                        "event_hash": getattr(record, "event_hash", ""),
                        "mismatched_fields": list(mismatches),
                    },
                    correlation_id=correlation_id,
                    now_ms=now_ms,
                )

            outcome_text = body.get("outcome")
            try:
                outcome = ReceiptOutcome(outcome_text)
            except (TypeError, ValueError):
                return self._commit_quarantine(
                    tx,
                    snapshot,
                    reason="INVALID_RECEIPT_OUTCOME",
                    incident_type="RECEIPT_QUARANTINED",
                    details={"receipt_id": receipt_id},
                    correlation_id=correlation_id,
                    now_ms=now_ms,
                )

            post_id = body.get("platform_post_id")
            if outcome is ReceiptOutcome.POST_CREATED and is_placeholder_post_id(
                post_id if isinstance(post_id, str) else None
            ):
                return self._commit_quarantine(
                    tx,
                    snapshot,
                    reason="PLACEHOLDER_POST_ID",
                    incident_type="RECEIPT_QUARANTINED",
                    details={"receipt_id": receipt_id, "platform_post_id": _safe_identifier(post_id)},
                    correlation_id=correlation_id,
                    now_ms=now_ms,
                )

            try:
                receipt = _to_domain_receipt(record, body, outcome)
            except (TypeError, ValueError):
                return self._commit_quarantine(
                    tx,
                    snapshot,
                    reason="INVALID_RECEIPT_BODY",
                    incident_type="RECEIPT_QUARANTINED",
                    details={"receipt_id": receipt_id},
                    correlation_id=correlation_id,
                    now_ms=now_ms,
                )
            execution = snapshot.execution
            delivery = snapshot.delivery
            if execution is None or delivery is None:
                return self._commit_quarantine(
                    tx,
                    snapshot,
                    reason="EXECUTION_OR_DELIVERY_MISSING",
                    incident_type="RECEIPT_QUARANTINED",
                    details={"receipt_id": receipt_id},
                    correlation_id=correlation_id,
                    now_ms=now_ms,
                )

            if delivery.state in {DeliveryState.REPORTED_PUBLISHED, DeliveryState.PUBLISHED}:
                if (
                    outcome is ReceiptOutcome.POST_CREATED
                    and execution.platform_post_id is not None
                    and execution.platform_post_id != receipt.platform_post_id
                ):
                    return self._commit_quarantine(
                        tx,
                        snapshot,
                        reason="DUPLICATE_PLATFORM_POST",
                        incident_type="DUPLICATE_POST",
                        severity="CRITICAL",
                        details={
                            "receipt_id": receipt_id,
                            "first_platform_post_id": execution.platform_post_id,
                            "second_platform_post_id": receipt.platform_post_id,
                        },
                        correlation_id=correlation_id,
                        now_ms=now_ms,
                    )
                return self._commit_stale(tx, snapshot, correlation_id, now_ms)

            if (
                execution.state is ExecutionState.REPORTED
                and outcome is ReceiptOutcome.POST_CREATED
                and execution.platform_post_id != receipt.platform_post_id
            ):
                return self._commit_quarantine(
                    tx,
                    snapshot,
                    reason="DUPLICATE_PLATFORM_POST",
                    incident_type="DUPLICATE_POST",
                    severity="CRITICAL",
                    details={
                        "receipt_id": receipt_id,
                        "first_platform_post_id": execution.platform_post_id,
                        "second_platform_post_id": receipt.platform_post_id,
                    },
                    correlation_id=correlation_id,
                    now_ms=now_ms,
                )

            if execution.state is ExecutionState.REPORTED and outcome is not ReceiptOutcome.POST_CREATED:
                return self._commit_stale(tx, snapshot, correlation_id, now_ms)

            if execution.state is ExecutionState.NO_SIDE_EFFECT and outcome is ReceiptOutcome.POST_CREATED:
                return self._commit_quarantine(
                    tx,
                    snapshot,
                    reason="POST_REPORTED_AFTER_NO_SIDE_EFFECT",
                    incident_type="RECEIPT_CONFLICT",
                    severity="CRITICAL",
                    details={"receipt_id": receipt_id, "platform_post_id": receipt.platform_post_id},
                    correlation_id=correlation_id,
                    now_ms=now_ms,
                )

            if delivery.state is DeliveryState.UNKNOWN and outcome is not ReceiptOutcome.POST_CREATED:
                return self._commit_stale(tx, snapshot, correlation_id, now_ms)
            if delivery.state not in {DeliveryState.EXECUTING, DeliveryState.UNKNOWN}:
                return self._commit_stale(tx, snapshot, correlation_id, now_ms)

            try:
                if outcome is ReceiptOutcome.POST_CREATED:
                    updated_execution = execution.accept_receipt(receipt)
                    updated_delivery, _events = delivery.apply(
                        DeliveryEvent.RECEIPT_CREATED,
                        {
                            "now_ms": now_ms,
                            "receipt_matches": True,
                            "platform_post_id_valid": True,
                            "post_id_matches_page": True,
                        },
                    )
                    permalink = body.get("permalink")
                    if isinstance(permalink, str) and permalink.startswith("https://"):
                        updated_delivery = replace(updated_delivery, permalink=permalink)
                    processing_state = "APPLIED"
                    verify_at_ms = now_ms + 5 * 60_000
                    incident = None
                elif outcome is ReceiptOutcome.OUTCOME_UNKNOWN:
                    updated_execution = execution.accept_receipt(receipt)
                    updated_delivery, _events = delivery.apply(
                        DeliveryEvent.RECEIPT_UNKNOWN,
                        {"now_ms": now_ms},
                    )
                    processing_state = "APPLIED"
                    verify_at_ms = None
                    incident = _incident(
                        "UNKNOWN",
                        snapshot,
                        severity="HIGH",
                        details={"receipt_id": receipt_id, "outcome": outcome.value},
                        incident_id=self._ids.new_id(),
                        at_ms=now_ms,
                    )
                else:
                    error_class = receipt.error_class or ""
                    retryable = self._error_classes.retryable_for(error_class)
                    updated_execution = execution.accept_receipt(
                        receipt,
                        error_class_verified=retryable is not None,
                    )
                    if retryable is None:
                        event = DeliveryEvent.RECEIPT_UNKNOWN
                        incident = _incident(
                            "UNKNOWN",
                            snapshot,
                            severity="HIGH",
                            details={
                                "receipt_id": receipt_id,
                                "error_class": error_class,
                                "reason": "UNVERIFIED_ERROR_CLASS",
                            },
                            incident_id=self._ids.new_id(),
                            at_ms=now_ms,
                        )
                    else:
                        event = (
                            DeliveryEvent.RECEIPT_NO_SIDE_EFFECT_RETRYABLE
                            if retryable
                            else DeliveryEvent.RECEIPT_NO_SIDE_EFFECT_NON_RETRYABLE
                        )
                        incident = None
                    updated_delivery, _events = delivery.apply(
                        event,
                        {"now_ms": now_ms, "error_class_verified": retryable is not None},
                    )
                    processing_state = "APPLIED"
                    verify_at_ms = None
            except (ValueError, DomainError):
                return self._commit_quarantine(
                    tx,
                    snapshot,
                    reason="RECEIPT_STATE_CONFLICT",
                    incident_type="RECEIPT_QUARANTINED",
                    details={"receipt_id": receipt_id},
                    correlation_id=correlation_id,
                    now_ms=now_ms,
                )

            committed = tx.commit_apply(
                snapshot,
                execution=updated_execution,
                delivery=updated_delivery,
                processing_state=processing_state,
                reason=None,
                verify_at_ms=verify_at_ms,
                incident=incident,
                audit_id=self._ids.new_id(),
                correlation_id=correlation_id,
                at_ms=now_ms,
            )
            if not committed:
                return ApplyReceiptResult("IGNORED_STALE", "CONCURRENT_UPDATE")
            return ApplyReceiptResult(
                processing_state=processing_state,
                delivery_state=updated_delivery.state.value,
                execution_state=updated_execution.state.value,
            )

    def _commit_quarantine(
        self,
        tx: ReceiptApplyTransaction,
        snapshot: ReceiptApplySnapshot,
        *,
        reason: str,
        incident_type: str,
        details: dict[str, object],
        correlation_id: str,
        now_ms: int,
        severity: str = "HIGH",
    ) -> ApplyReceiptResult:
        incident = _incident(
            incident_type,
            snapshot,
            severity=severity,
            details=details,
            incident_id=self._ids.new_id(),
            at_ms=now_ms,
        )
        committed = tx.commit_apply(
            snapshot,
            execution=None,
            delivery=None,
            processing_state="QUARANTINED",
            reason=reason,
            verify_at_ms=None,
            incident=incident,
            audit_id=self._ids.new_id(),
            correlation_id=correlation_id,
            at_ms=now_ms,
        )
        return ApplyReceiptResult(
            "QUARANTINED" if committed else "IGNORED_STALE",
            reason=reason,
            delivery_state=_delivery_state(snapshot.delivery),
            execution_state=_execution_state(snapshot.execution),
        )

    def _commit_stale(
        self,
        tx: ReceiptApplyTransaction,
        snapshot: ReceiptApplySnapshot,
        correlation_id: str,
        now_ms: int,
    ) -> ApplyReceiptResult:
        tx.commit_apply(
            snapshot,
            execution=None,
            delivery=None,
            processing_state="IGNORED_STALE",
            reason=None,
            verify_at_ms=None,
            incident=None,
            audit_id=self._ids.new_id(),
            correlation_id=correlation_id,
            at_ms=now_ms,
        )
        return ApplyReceiptResult(
            "IGNORED_STALE",
            delivery_state=_delivery_state(snapshot.delivery),
            execution_state=_execution_state(snapshot.execution),
        )


def _identity_mismatches(
    snapshot: ReceiptApplySnapshot,
    body: Mapping[str, object],
) -> tuple[str, ...]:
    record = snapshot.record
    execution = snapshot.execution
    delivery = snapshot.delivery
    expected_delivery_id = (
        delivery.id
        if delivery is not None
        else execution.delivery_id if execution is not None else None
    )
    expected = {
        "issuer_id": (getattr(record, "issuer_id", None), snapshot.principal_id),
        "event_id": (body.get("event_id"), getattr(record, "event_id", None)),
        "execution_id": (body.get("execution_id"), None if execution is None else execution.id),
        "grant_id": (body.get("grant_id"), None if execution is None else execution.grant_id),
        "command_id": (body.get("command_id"), snapshot.command_id),
        "execution_command_id": (None if execution is None else execution.command_id, snapshot.command_id),
        "delivery_id": (body.get("delivery_id"), expected_delivery_id),
        "execution_delivery_id": (None if execution is None else execution.delivery_id, None if delivery is None else delivery.id),
        "revision_id": (body.get("revision_id"), snapshot.revision_id),
        "channel_id": (body.get("channel_id"), snapshot.channel_id),
        "remote_page_id": (body.get("remote_page_id"), snapshot.remote_page_id),
        "payload_hash": (body.get("payload_hash"), snapshot.payload_hash),
    }
    return tuple(name for name, (actual, required) in expected.items() if required is None or actual != required)


def _to_domain_receipt(record: object, body: Mapping[str, object], outcome: ReceiptOutcome) -> Receipt:
    error = body.get("error")
    error_class = error.get("class") if isinstance(error, Mapping) else None
    return Receipt(
        issuer=str(getattr(record, "issuer_id", "")),
        event_id=str(body.get("event_id", "")),
        execution_id=str(body.get("execution_id", "")),
        grant_id=str(body.get("grant_id", "")),
        command_id=str(body.get("command_id", "")),
        delivery_id=str(body.get("delivery_id", "")),
        revision_id=str(body.get("revision_id", "")),
        channel_id=str(body.get("channel_id", "")),
        remote_account_id=str(body.get("remote_page_id", "")),
        payload_hash=str(body.get("payload_hash", "")),
        outcome=outcome,
        platform_post_id=(body.get("platform_post_id") if isinstance(body.get("platform_post_id"), str) else None),
        error_class=error_class if isinstance(error_class, str) else None,
    )


def _incident(
    incident_type: str,
    snapshot: ReceiptApplySnapshot,
    *,
    severity: str,
    details: dict[str, object],
    incident_id: str,
    at_ms: int,
) -> dict[str, object]:
    return {
        "incident_type": incident_type,
        "channel_id": snapshot.channel_id or None,
        "ref": snapshot.delivery.id if snapshot.delivery is not None else snapshot.command_id,
        "severity": severity,
        "details": details,
        "incident_id": incident_id,
        "at_ms": at_ms,
    }


def _safe_identifier(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    return value[:128]


def _delivery_state(delivery: Delivery | None) -> str | None:
    return None if delivery is None else delivery.state.value


def _execution_state(execution: Execution | None) -> str | None:
    return None if execution is None else execution.state.value
