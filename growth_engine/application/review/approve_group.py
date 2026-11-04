from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from growth_engine.application.errors import Conflict
from growth_engine.application.ports.clock import Clock
from growth_engine.domain.delivery.approval import ApprovalDecision
from growth_engine.domain.kernel.errors import DomainError, ErrorCode
from growth_engine.domain.kernel.hashing import canonical_json_bytes, sha256_hex


@dataclass(frozen=True)
class ApprovalItem:
    delivery_id: str
    revision_id: str
    payload_hash: str
    expected_row_version: int


@dataclass(frozen=True)
class ApprovalConflict:
    delivery_id: str
    code: str
    current_row_version: int | None

    def as_dict(self) -> dict[str, object]:
        return {
            "delivery_id": self.delivery_id,
            "code": self.code,
            "current_row_version": self.current_row_version,
        }


@dataclass(frozen=True)
class ApprovalBatchResult:
    approvals: tuple[ApprovalDecision, ...] = ()
    replayed: bool = False
    conflicts: tuple[ApprovalConflict, ...] = ()


class ApprovalBatchStore(Protocol):
    """One BEGIN IMMEDIATE boundary for idempotency, revalidation and the whole batch.

    The adapter re-reads every delivery/revision/QC/facts/channel in the transaction.
    Any conflict rolls back all approvals; success appends approvals/audit and stores
    the idempotency response. It must never enqueue publish commands here.
    """

    def approve_batch(
        self,
        items: tuple[ApprovalItem, ...],
        *,
        actor: str,
        principal: str,
        idempotency_key: str,
        request_hash: str,
        approved_at_ms: int,
    ) -> ApprovalBatchResult: ...


class ApproveGroup:
    def __init__(self, store: ApprovalBatchStore, clock: Clock) -> None:
        self._store = store
        self._clock = clock

    def execute(
        self,
        items: Sequence[ApprovalItem],
        *,
        actor: str,
        principal: str,
        idempotency_key: str,
    ) -> ApprovalBatchResult:
        if not actor.strip() or not principal.strip() or not idempotency_key.strip():
            raise ValueError("actor, principal and idempotency_key are required")
        if not items:
            raise ValueError("at least one approval item is required")
        canonical_items = tuple(sorted(items, key=lambda item: item.delivery_id))
        if len({item.delivery_id for item in canonical_items}) != len(canonical_items):
            raise ValueError("a delivery may appear only once in an approval batch")
        for item in canonical_items:
            if not item.delivery_id.strip() or not item.revision_id.strip():
                raise ValueError("delivery_id and revision_id are required")
            if len(item.payload_hash) != 64 or any(
                char not in "0123456789abcdefABCDEF" for char in item.payload_hash
            ):
                raise ValueError("payload_hash must be a SHA-256 hex digest")
            if type(item.expected_row_version) is not int or item.expected_row_version < 1:
                raise ValueError("expected_row_version must be a positive integer")

        request_hash = sha256_hex(
            canonical_json_bytes(
                {
                    "items": [
                        {
                            "delivery_id": item.delivery_id,
                            "revision_id": item.revision_id,
                            "payload_hash": item.payload_hash,
                            "expected_row_version": item.expected_row_version,
                        }
                        for item in canonical_items
                    ]
                }
            )
        )
        result = self._store.approve_batch(
            canonical_items,
            actor=actor,
            principal=principal,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            approved_at_ms=self._clock.now_ms(),
        )
        if result.conflicts:
            raise Conflict(
                "Một hoặc nhiều bài đã thay đổi; không có bài nào được duyệt.",
                {"conflicts": [item.as_dict() for item in result.conflicts]},
            )
        if not result.approvals:
            raise DomainError(ErrorCode.STATE_CONFLICT, "Không có approval để trả về.")
        return result


def approve_group(
    use_case: ApproveGroup,
    items: Sequence[ApprovalItem],
    *,
    actor: str,
    principal: str,
    idempotency_key: str,
) -> ApprovalBatchResult:
    return use_case.execute(
        items,
        actor=actor,
        principal=principal,
        idempotency_key=idempotency_key,
    )
