from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Protocol

from growth_engine.application.ports.clock import Clock, IdGenerator
from growth_engine.domain.kernel.errors import DomainError, ErrorCode
from growth_engine.domain.kernel.hashing import canonical_json_bytes


@dataclass(frozen=True)
class ReceiveReceiptCommand:
    issuer_id: str
    body: Mapping[str, object]
    correlation_id: str


@dataclass(frozen=True)
class ReceiptInboxRecord:
    id: str
    issuer_id: str
    event_id: str
    event_hash: str
    body: Mapping[str, object]
    received_at_ms: int
    processing_state: str = "RECEIVED"
    quarantine_reason: str | None = None


@dataclass(frozen=True)
class ReceiveReceiptResult:
    receipt_id: str
    accepted: bool = True
    duplicate: bool = False


class ReceiptPersistenceUnavailable(RuntimeError):
    """Storage adapters raise this when receipt or its apply job cannot be committed."""


class ReceiveReceiptTransaction(Protocol):
    def find_receipt(self, issuer_id: str, event_id: str) -> ReceiptInboxRecord | None: ...
    def insert_receipt(self, record: ReceiptInboxRecord) -> None: ...

    def enqueue_apply_receipt(
        self,
        receipt_id: str,
        job_id: str,
        *,
        run_at_ms: int,
        correlation_id: str,
    ) -> None: ...

    def record_incident(self, **incident: object) -> None: ...
    def append_audit(self, **entry: object) -> None: ...


class ReceiveReceiptStore(Protocol):
    def begin_immediate(self) -> AbstractContextManager[ReceiveReceiptTransaction]: ...


class ReceiveReceipt:
    """Durably accept and deduplicate Make callbacks before asynchronous application."""

    def __init__(self, store: ReceiveReceiptStore, clock: Clock, ids: IdGenerator) -> None:
        self._store = store
        self._clock = clock
        self._ids = ids

    def execute(self, command: ReceiveReceiptCommand) -> ReceiveReceiptResult:
        _validate_command(command)
        now_ms = self._clock.now_ms()
        body = _sanitize_body(command.body)
        event_id = str(body["event_id"])
        event_hash = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
        conflict = False
        duplicate: ReceiptInboxRecord | None = None

        with self._store.begin_immediate() as tx:
            existing = tx.find_receipt(command.issuer_id, event_id)
            if existing is not None:
                if existing.event_hash == event_hash:
                    duplicate = existing
                else:
                    conflict = True
                    incoming_post_id = body.get("platform_post_id")
                    existing_post_id = existing.body.get("platform_post_id")
                    conflict_details = {
                        "event_id": event_id,
                        "existing_hash": existing.event_hash,
                        "incoming_hash": event_hash,
                        "incoming_body": body,
                    }
                    tx.record_incident(
                        incident_type="RECEIPT_CONFLICT",
                        channel_id=_optional_text(existing.body.get("channel_id")),
                        ref=f"{command.issuer_id}:{event_id}",
                        severity="CRITICAL",
                        details=conflict_details,
                        incident_id=self._ids.new_id(),
                        at_ms=now_ms,
                        correlation_id=command.correlation_id,
                    )
                    if (
                        existing.body.get("outcome") == "POST_CREATED"
                        and body.get("outcome") == "POST_CREATED"
                        and existing.body.get("delivery_id") == body.get("delivery_id")
                        and existing.body.get("remote_page_id") == body.get("remote_page_id")
                        and isinstance(existing_post_id, str)
                        and isinstance(incoming_post_id, str)
                        and existing_post_id.strip()
                        and incoming_post_id.strip()
                        and existing_post_id != incoming_post_id
                    ):
                        tx.record_incident(
                            incident_type="DUPLICATE_POST",
                            channel_id=_optional_text(existing.body.get("channel_id")),
                            ref=str(existing.body.get("delivery_id", "")),
                            severity="CRITICAL",
                            details={
                                "first_platform_post_id": existing_post_id,
                                "second_platform_post_id": incoming_post_id,
                                "event_id": event_id,
                                "incoming_hash": event_hash,
                                "incoming_body": body,
                            },
                            incident_id=self._ids.new_id(),
                            at_ms=now_ms,
                            correlation_id=command.correlation_id,
                        )
                    tx.append_audit(
                        audit_id=self._ids.new_id(),
                        aggregate_type="receipt",
                        aggregate_id=existing.id,
                        action="receipt_conflict",
                        details=conflict_details,
                        correlation_id=command.correlation_id,
                        at_ms=now_ms,
                    )
            else:
                record = ReceiptInboxRecord(
                    id=self._ids.new_id(),
                    issuer_id=command.issuer_id,
                    event_id=event_id,
                    event_hash=event_hash,
                    body=body,
                    received_at_ms=now_ms,
                )
                tx.insert_receipt(record)
                tx.enqueue_apply_receipt(
                    record.id,
                    self._ids.new_id(),
                    run_at_ms=now_ms,
                    correlation_id=command.correlation_id,
                )

        if conflict:
            raise DomainError(
                ErrorCode.RECEIPT_CONFLICT,
                "Đã nhận kết quả đăng mâu thuẫn; bản đầu được giữ nguyên và đã mở sự cố.",
            )
        if duplicate is not None:
            return ReceiveReceiptResult(receipt_id=duplicate.id, duplicate=True)
        return ReceiveReceiptResult(receipt_id=record.id)


def _validate_command(command: ReceiveReceiptCommand) -> None:
    if not isinstance(command.issuer_id, str) or not command.issuer_id.strip():
        raise DomainError(ErrorCode.VALIDATION, "Nguồn gửi receipt không hợp lệ.")
    if not isinstance(command.correlation_id, str) or not command.correlation_id.strip():
        raise DomainError(ErrorCode.VALIDATION, "Correlation ID không hợp lệ.")
    if not isinstance(command.body, Mapping):
        raise DomainError(ErrorCode.VALIDATION, "Receipt không hợp lệ.")
    body = command.body
    for name in (
        "schema_version",
        "event_id",
        "command_id",
        "execution_id",
        "grant_id",
        "delivery_id",
        "revision_id",
        "channel_id",
        "remote_page_id",
        "payload_hash",
        "outcome",
    ):
        if not isinstance(body.get(name), str) or not str(body[name]).strip():
            raise DomainError(ErrorCode.VALIDATION, "Receipt thiếu trường bắt buộc.")
    if body.get("schema_version") != "growth.receipt.v2":
        raise DomainError(ErrorCode.VALIDATION, "Phiên bản receipt không hợp lệ.")
    if body.get("outcome") not in {"POST_CREATED", "REJECTED_NO_SIDE_EFFECT", "OUTCOME_UNKNOWN"}:
        raise DomainError(ErrorCode.VALIDATION, "Kết quả receipt không hợp lệ.")
    if body.get("event_id") != f"{body.get('grant_id')}:{body.get('outcome')}":
        raise DomainError(ErrorCode.VALIDATION, "Event ID receipt không khớp grant và kết quả.")
    payload_hash = body.get("payload_hash")
    if not re.fullmatch(r"[0-9a-f]{64}", payload_hash):
        raise DomainError(ErrorCode.VALIDATION, "Payload hash receipt không hợp lệ.")
    if type(body.get("occurred_at_ms")) is not int or body["occurred_at_ms"] < 0:
        raise DomainError(ErrorCode.VALIDATION, "Thời điểm receipt không hợp lệ.")
    error = body.get("error")
    if error is not None:
        if (
            not isinstance(error, Mapping)
            or not isinstance(error.get("class"), str)
            or not error["class"].strip()
            or not re.fullmatch(r"[A-Z0-9_.-]{1,128}", error["class"])
            or not isinstance(error.get("message"), str)
        ):
            raise DomainError(ErrorCode.VALIDATION, "Thông tin lỗi receipt không hợp lệ.")
    if body.get("outcome") == "REJECTED_NO_SIDE_EFFECT" and error is None:
        raise DomainError(ErrorCode.VALIDATION, "Receipt bị từ chối phải có mã lỗi.")


def _sanitize_body(source: Mapping[str, object]) -> dict[str, object]:
    body = dict(source)
    permalink = body.get("permalink")
    if isinstance(permalink, str):
        permalink = _URL_CREDENTIALS.sub(r"\1[REDACTED]@", permalink)
        permalink = _URL_QUERY.sub(r"\1", permalink)
        body["permalink"] = permalink
    error = body.get("error")
    if isinstance(error, Mapping):
        safe_error = dict(error)
        safe_error["message"] = _redact_message(str(safe_error.get("message", "")))
        body["error"] = safe_error
    return body


_SENSITIVE_ASSIGNMENT = re.compile(
    r"(?i)(authorization|access[_-]?token|token|secret|password|api[_-]?key)\s*[:=]\s*[^\s,;&]+"
)
_BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*")
_URL_QUERY = re.compile(r"(https?://[^\s?]+)\?[^\s]+", re.IGNORECASE)
_URL_CREDENTIALS = re.compile(r"(?i)(https?://)[^/@\s]+@")
_LONG_TOKEN = re.compile(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{40,}(?![A-Za-z0-9_-])")


def _redact_message(message: str) -> str:
    safe = _BEARER.sub("Bearer [REDACTED]", message)
    safe = _SENSITIVE_ASSIGNMENT.sub(lambda match: f"{match.group(1)}=[REDACTED]", safe)
    safe = _URL_CREDENTIALS.sub(r"\1[REDACTED]@", safe)
    safe = _URL_QUERY.sub(r"\1?[REDACTED]", safe)
    safe = _LONG_TOKEN.sub("[REDACTED]", safe)
    return safe[:1_024]


def _optional_text(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None
