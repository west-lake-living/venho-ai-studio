from __future__ import annotations

import pytest

from growth_engine.application.errors import Conflict
from growth_engine.application.review.approve_group import (
    ApprovalBatchResult,
    ApprovalConflict,
    ApprovalItem,
    ApproveGroup,
)
from growth_engine.domain.delivery.approval import ApprovalDecision, ApprovalType
from growth_engine.domain.kernel.errors import DomainError, ErrorCode
from tests.growth_engine.support.fakes import FakeClock


def test_batch_with_one_stale_item_changes_none_and_returns_all_conflicts() -> None:
    store = _ApprovalStore(stale_ids={"delivery-b"})
    use_case = ApproveGroup(store, FakeClock(500))

    with pytest.raises(Conflict) as caught:
        use_case.execute(
            _items(), actor="operator-1", principal="bff", idempotency_key="batch-1"
        )

    assert caught.value.details["conflicts"] == [
        {"delivery_id": "delivery-b", "code": "ERR_GC2_REVISION_CONFLICT", "current_row_version": 8}
    ]
    assert store.approvals == ()
    assert store.commands == []


def test_batch_approval_is_idempotent_and_never_enqueues_publish_command() -> None:
    store = _ApprovalStore()
    use_case = ApproveGroup(store, FakeClock(500))
    args = dict(actor="operator-1", principal="bff", idempotency_key="batch-1")

    first = use_case.execute(_items(), **args)
    replay = use_case.execute(_items(), **args)

    assert len(first.approvals) == 2
    assert replay == first
    assert store.approval_writes == 1
    assert store.commands == []


def test_reusing_idempotency_key_with_different_batch_returns_mismatch() -> None:
    store = _ApprovalStore()
    use_case = ApproveGroup(store, FakeClock(500))
    args = dict(actor="operator-1", principal="bff", idempotency_key="batch-1")
    use_case.execute(_items(), **args)

    with pytest.raises(DomainError) as caught:
        use_case.execute(_items()[:1], **args)

    assert caught.value.code == ErrorCode.IDEMPOTENCY_MISMATCH.value


class _ApprovalStore:
    """Synthetic adapter: validates the whole batch before making any approval visible."""

    def __init__(self, *, stale_ids: set[str] | None = None) -> None:
        self.stale_ids = stale_ids or set()
        self.records: dict[str, tuple[str, ApprovalBatchResult]] = {}
        self.approvals = ()
        self.commands: list[object] = []
        self.approval_writes = 0

    def approve_batch(
        self, items, *, actor, principal, idempotency_key, request_hash, approved_at_ms
    ) -> ApprovalBatchResult:
        existing = self.records.get((principal, idempotency_key))
        if existing:
            old_hash, result = existing
            if old_hash != request_hash:
                raise DomainError(ErrorCode.IDEMPOTENCY_MISMATCH, "idempotency mismatch")
            return result
        conflicts = tuple(
            ApprovalConflict(item.delivery_id, "ERR_GC2_REVISION_CONFLICT", 8)
            for item in items
            if item.delivery_id in self.stale_ids
        )
        if conflicts:
            return ApprovalBatchResult(conflicts=conflicts)
        approvals = tuple(
            ApprovalDecision(
                f"approval-{item.delivery_id}", item.revision_id, item.payload_hash,
                ApprovalType.APPROVE, actor, approved_at_ms,
            )
            for item in items
        )
        result = ApprovalBatchResult(approvals=approvals)
        self.approvals = approvals
        self.approval_writes += 1
        self.records[(principal, idempotency_key)] = (request_hash, result)
        return result


def _items() -> tuple[ApprovalItem, ApprovalItem]:
    return (
        ApprovalItem("delivery-a", "revision-a", "a" * 64, 4),
        ApprovalItem("delivery-b", "revision-b", "b" * 64, 7),
    )
