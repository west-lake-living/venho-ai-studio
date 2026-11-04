from __future__ import annotations

import hashlib
import json
import threading
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Iterator

import jsonschema
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from growth_engine.adapters.inbound.api.app import create_app
from growth_engine.adapters.inbound.api.routers.internal_receipts import router
from growth_engine.application.publishing.apply_receipt import ApplyReceipt, ReceiptApplySnapshot
from growth_engine.application.publishing.receive_receipt import (
    ReceiptPersistenceUnavailable,
    ReceiveReceipt,
    ReceiveReceiptCommand,
    ReceiptInboxRecord,
)
from growth_engine.application.publishing.watch_receipt_timeouts import WatchReceiptTimeouts
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.states import DeliveryState
from growth_engine.domain.publishing.execution import Execution, ExecutionState
from growth_engine.domain.kernel.errors import DomainError


CHANNEL_ID = "channel-synthetic-hanoi"
CHANNEL_KEY = "fb_hanoi"
PAGE_ID = "remote-page-synthetic-hanoi"
COMMAND_ID = "command-synthetic-001"
EXECUTION_ID = "execution-synthetic-001"
GRANT_ID = "grant-synthetic-001"
DELIVERY_ID = "delivery-synthetic-001"
REVISION_ID = "revision-synthetic-001"
PAYLOAD_HASH = "a" * 64
NOW_MS = 1_800_000_000_000
RECEIPT_DUE_MS = NOW_MS + 60_000


class FakeClock:
    def __init__(self, value: int = NOW_MS) -> None:
        self.value = value

    def now_ms(self) -> int:
        return self.value


class FakeIds:
    def __init__(self) -> None:
        self.counter = 0

    def new_id(self) -> str:
        self.counter += 1
        return f"synthetic-id-{self.counter}"


class FakeReceiptStore:
    def __init__(self) -> None:
        self.records: dict[str, ReceiptInboxRecord] = {}
        self.by_key: dict[tuple[str, str], str] = {}
        self.snapshots: dict[str, ReceiptApplySnapshot] = {}
        self.jobs: list[tuple[str, str, int]] = []
        self.incidents: list[dict[str, object]] = []
        self.audit: list[dict[str, object]] = []
        self.timeout_candidates: list[ReceiptApplySnapshot] = []
        self._lock = threading.RLock()

    @contextmanager
    def begin_immediate(self) -> Iterator["FakeReceiptStore"]:
        with self._lock:
            yield self

    def find_receipt(self, issuer_id: str, event_id: str) -> ReceiptInboxRecord | None:
        receipt_id = self.by_key.get((issuer_id, event_id))
        return None if receipt_id is None else self.records[receipt_id]

    def insert_receipt(self, record: ReceiptInboxRecord) -> None:
        self.records[record.id] = record
        self.by_key[(record.issuer_id, record.event_id)] = record.id

    def enqueue_apply_receipt(
        self,
        receipt_id: str,
        job_id: str,
        *,
        run_at_ms: int,
        correlation_id: str,
    ) -> None:
        self.jobs.append((receipt_id, job_id, run_at_ms))

    def record_incident(self, **incident: object) -> None:
        self.incidents.append(dict(incident))

    def append_audit(self, **entry: object) -> None:
        self.audit.append(dict(entry))

    def load_for_apply(self, receipt_id: str) -> ReceiptApplySnapshot | None:
        return self.snapshots.get(receipt_id)

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
    ) -> bool:
        stored = self.records[snapshot.record.id]
        self.records[stored.id] = replace(
            stored,
            processing_state=processing_state,
            quarantine_reason=reason,
        )
        if incident is not None:
            self.incidents.append(dict(incident))
        self.audit.append({"id": audit_id, "receipt_id": stored.id, "at_ms": at_ms})
        if verify_at_ms is not None:
            self.jobs.append((stored.id, "verify_publication", verify_at_ms))
        updated = replace(
            snapshot,
            execution=execution if execution is not None else snapshot.execution,
            delivery=delivery if delivery is not None else snapshot.delivery,
        )
        self.snapshots[stored.id] = updated
        return True

    def list_due_receipt_timeouts(self, now_ms: int, limit: int) -> list[ReceiptApplySnapshot]:
        return [
            candidate
            for candidate in self.timeout_candidates
            if candidate.execution is not None
            and candidate.execution.state is ExecutionState.AUTHORIZED
            and now_ms > candidate.execution.receipt_due_at_ms
        ][:limit]

    def commit_timeout(
        self,
        candidate: ReceiptApplySnapshot,
        *,
        execution: Execution,
        delivery: Delivery,
        incident: dict[str, object],
        audit_id: str,
        correlation_id: str,
        at_ms: int,
    ) -> bool:
        index = self.timeout_candidates.index(candidate)
        self.timeout_candidates[index] = replace(candidate, execution=execution, delivery=delivery)
        self.incidents.append(dict(incident))
        self.audit.append({"id": audit_id, "execution_id": execution.id, "at_ms": at_ms})
        return True


class NoErrorClassIsVerified:
    def retryable_for(self, error_class: str) -> bool | None:
        return None


class FakeErrorClasses:
    def __init__(self, values: dict[str, bool]) -> None:
        self.values = values

    def retryable_for(self, error_class: str) -> bool | None:
        return self.values.get(error_class)


def make_body(
    *,
    outcome: str = "POST_CREATED",
    post_id: str | None = "post-synthetic-001",
    page_id: str = PAGE_ID,
    payload_hash: str = PAYLOAD_HASH,
    grant_id: str = GRANT_ID,
    error: dict[str, str] | None = None,
) -> dict[str, object]:
    if error is None and outcome == "REJECTED_NO_SIDE_EFFECT":
        error = {"class": "MAKE_HTTP_400", "message": "synthetic rejected"}
    return {
        "schema_version": "growth.receipt.v2",
        "event_id": f"{grant_id}:{outcome}",
        "command_id": COMMAND_ID,
        "execution_id": EXECUTION_ID,
        "grant_id": grant_id,
        "delivery_id": DELIVERY_ID,
        "revision_id": REVISION_ID,
        "channel_id": CHANNEL_ID,
        "remote_page_id": page_id,
        "payload_hash": payload_hash,
        "outcome": outcome,
        "platform_post_id": post_id,
        "permalink": "https://facebook.com/posts/synthetic" if post_id else None,
        "failed_step": "CREATE_POST" if outcome == "REJECTED_NO_SIDE_EFFECT" else None,
        "error": error,
        "occurred_at_ms": NOW_MS,
    }


def make_execution(state: ExecutionState = ExecutionState.AUTHORIZED) -> Execution:
    return Execution(
        id=EXECUTION_ID,
        delivery_id=DELIVERY_ID,
        command_id=COMMAND_ID,
        grant_id=GRANT_ID,
        state=state,
        grant_expires_at_ms=NOW_MS + 30_000,
        receipt_due_at_ms=RECEIPT_DUE_MS,
        platform_post_id="post-synthetic-001" if state is ExecutionState.REPORTED else None,
    )


def make_snapshot(
    receipt_id: str,
    body: dict[str, object],
    *,
    execution: Execution | None = None,
    delivery: Delivery | None = None,
) -> ReceiptApplySnapshot:
    record = ReceiptInboxRecord(
        id=receipt_id,
        issuer_id="make-fb-hanoi",
        event_id=body["event_id"],
        event_hash=hashlib.sha256(str(body).encode("utf-8")).hexdigest(),
        body=body,
        received_at_ms=NOW_MS,
        processing_state="RECEIVED",
    )
    return ReceiptApplySnapshot(
        record=record,
        execution=execution if execution is not None else make_execution(),
        delivery=delivery if delivery is not None else Delivery(DELIVERY_ID, DeliveryState.EXECUTING),
        command_id=COMMAND_ID,
        revision_id=REVISION_ID,
        channel_id=CHANNEL_ID,
        remote_page_id=PAGE_ID,
        payload_hash=PAYLOAD_HASH,
        principal_id="make-fb-hanoi",
    )


def receiver(store: FakeReceiptStore, clock: FakeClock | None = None) -> ReceiveReceipt:
    return ReceiveReceipt(store, clock or FakeClock(), FakeIds())


def receipt_command(body: dict[str, object]) -> ReceiveReceiptCommand:
    return ReceiveReceiptCommand(
        issuer_id="make-fb-hanoi",
        body=body,
        correlation_id="corr-synthetic-001",
    )


def test_duplicate_receipt_same_hash_acknowledges_original_without_second_job() -> None:
    store = FakeReceiptStore()
    use_case = receiver(store)
    body = make_body()

    first = use_case.execute(receipt_command(body))
    replay = use_case.execute(receipt_command(body))

    assert first.receipt_id == replay.receipt_id
    assert first.duplicate is False
    assert replay.duplicate is True
    assert len(store.records) == 1
    assert len(store.jobs) == 1


def test_receipt_conflict_keeps_first_and_opens_critical_duplicate_post_incident() -> None:
    store = FakeReceiptStore()
    use_case = receiver(store)
    first_body = make_body()
    first = use_case.execute(receipt_command(first_body))
    second_body = make_body(post_id="post-synthetic-002")

    with pytest.raises(DomainError) as error:
        use_case.execute(receipt_command(second_body))

    assert error.value.code == "ERR_GC2_RECEIPT_CONFLICT"
    assert store.records[first.receipt_id].body["platform_post_id"] == "post-synthetic-001"
    assert {incident["incident_type"] for incident in store.incidents} >= {
        "RECEIPT_CONFLICT",
        "DUPLICATE_POST",
    }
    assert len(store.jobs) == 1


def test_receipt_error_message_is_redacted_before_hash_and_storage() -> None:
    store = FakeReceiptStore()
    body = make_body(
        outcome="REJECTED_NO_SIDE_EFFECT",
        post_id=None,
        error={"class": "MAKE_HTTP_400", "message": "Bearer abc.def access_token=secret https://x.test/media?t=signed"},
    )
    body["permalink"] = "https://user:password@facebook.com/posts/x?access_token=signed"

    result = receiver(store).execute(receipt_command(body))
    safe_message = store.records[result.receipt_id].body["error"]["message"]

    assert "abc.def" not in safe_message
    assert "secret" not in safe_message
    assert "signed" not in safe_message
    assert "password" not in store.records[result.receipt_id].body["permalink"]


@pytest.mark.parametrize(
    ("field", "value"),
    [("remote_page_id", "remote-page-other"), ("payload_hash", "f" * 64), ("grant_id", "grant-other")],
)
def test_receipt_identity_mismatch_is_quarantined_without_delivery_change(field: str, value: str) -> None:
    store = FakeReceiptStore()
    body = make_body(**({"page_id": value} if field == "remote_page_id" else {field: value}))
    snapshot = make_snapshot("receipt-synthetic-001", body)
    store.records[snapshot.record.id] = snapshot.record
    store.snapshots[snapshot.record.id] = snapshot
    before = snapshot.delivery

    result = ApplyReceipt(store, FakeClock(), FakeIds(), NoErrorClassIsVerified()).execute(
        snapshot.record.id,
        correlation_id="corr-synthetic-001",
    )

    assert result.processing_state == "QUARANTINED"
    assert store.records[snapshot.record.id].quarantine_reason == "RECEIPT_IDENTITY_MISMATCH"
    assert store.snapshots[snapshot.record.id].delivery == before
    assert store.incidents[-1]["incident_type"] == "RECEIPT_QUARANTINED"


def test_placeholder_post_id_is_quarantined_and_never_reported() -> None:
    store = FakeReceiptStore()
    body = make_body(post_id="{{module.post_id}}")
    snapshot = make_snapshot("receipt-synthetic-001", body)
    store.records[snapshot.record.id] = snapshot.record
    store.snapshots[snapshot.record.id] = snapshot

    result = ApplyReceipt(store, FakeClock(), FakeIds(), NoErrorClassIsVerified()).execute(
        snapshot.record.id,
        correlation_id="corr-synthetic-001",
    )

    assert result.processing_state == "QUARANTINED"
    assert store.snapshots[snapshot.record.id].delivery.state is DeliveryState.EXECUTING
    assert store.snapshots[snapshot.record.id].execution.state is ExecutionState.AUTHORIZED


def test_post_created_receipt_transitions_and_queues_publication_verification() -> None:
    store = FakeReceiptStore()
    body = make_body()
    snapshot = make_snapshot("receipt-synthetic-001", body)
    store.records[snapshot.record.id] = snapshot.record
    store.snapshots[snapshot.record.id] = snapshot

    result = ApplyReceipt(store, FakeClock(), FakeIds(), NoErrorClassIsVerified()).execute(
        snapshot.record.id,
        correlation_id="corr-synthetic-001",
    )

    applied = store.snapshots[snapshot.record.id]
    assert result.processing_state == "APPLIED"
    assert applied.execution.state is ExecutionState.REPORTED
    assert applied.execution.platform_post_id == "post-synthetic-001"
    assert applied.delivery.state is DeliveryState.REPORTED_PUBLISHED
    assert applied.delivery.permalink == "https://facebook.com/posts/synthetic"
    assert store.jobs[-1][1] == "verify_publication"
    assert store.jobs[-1][2] == NOW_MS + 5 * 60_000


def test_late_error_after_success_is_ignored_stale_without_rolling_back_delivery() -> None:
    store = FakeReceiptStore()
    success = make_body()
    success_snapshot = make_snapshot("receipt-success", success)
    store.records[success_snapshot.record.id] = success_snapshot.record
    store.snapshots[success_snapshot.record.id] = success_snapshot
    ApplyReceipt(store, FakeClock(), FakeIds(), NoErrorClassIsVerified()).execute(
        success_snapshot.record.id,
        correlation_id="corr-synthetic-001",
    )
    late_error = make_body(outcome="REJECTED_NO_SIDE_EFFECT", post_id=None)
    error_snapshot = make_snapshot(
        "receipt-late-error",
        late_error,
        execution=store.snapshots[success_snapshot.record.id].execution,
        delivery=store.snapshots[success_snapshot.record.id].delivery,
    )
    store.records[error_snapshot.record.id] = error_snapshot.record
    store.snapshots[error_snapshot.record.id] = error_snapshot

    result = ApplyReceipt(store, FakeClock(), FakeIds(), FakeErrorClasses({"MAKE_HTTP_400": True})).execute(
        error_snapshot.record.id,
        correlation_id="corr-synthetic-001",
    )

    assert result.processing_state == "IGNORED_STALE"
    assert store.snapshots[error_snapshot.record.id].delivery.state is DeliveryState.REPORTED_PUBLISHED
    assert store.snapshots[error_snapshot.record.id].execution.platform_post_id == "post-synthetic-001"


def test_unverified_no_side_effect_error_becomes_unknown() -> None:
    store = FakeReceiptStore()
    body = make_body(outcome="REJECTED_NO_SIDE_EFFECT", post_id=None)
    snapshot = make_snapshot("receipt-error", body)
    store.records[snapshot.record.id] = snapshot.record
    store.snapshots[snapshot.record.id] = snapshot

    ApplyReceipt(store, FakeClock(), FakeIds(), NoErrorClassIsVerified()).execute(
        snapshot.record.id,
        correlation_id="corr-synthetic-001",
    )

    assert store.snapshots[snapshot.record.id].execution.state is ExecutionState.UNKNOWN
    assert store.snapshots[snapshot.record.id].delivery.state is DeliveryState.UNKNOWN
    assert store.incidents[-1]["incident_type"] == "UNKNOWN"


@pytest.mark.parametrize(
    ("retryable", "expected_delivery"),
    [(True, DeliveryState.BLOCKED), (False, DeliveryState.FAILED_FINAL)],
)
def test_verified_no_side_effect_error_uses_retryability_policy(
    retryable: bool,
    expected_delivery: DeliveryState,
) -> None:
    store = FakeReceiptStore()
    body = make_body(outcome="REJECTED_NO_SIDE_EFFECT", post_id=None)
    snapshot = make_snapshot("receipt-error", body)
    store.records[snapshot.record.id] = snapshot.record
    store.snapshots[snapshot.record.id] = snapshot

    ApplyReceipt(store, FakeClock(), FakeIds(), FakeErrorClasses({"MAKE_HTTP_400": retryable})).execute(
        snapshot.record.id,
        correlation_id="corr-synthetic-001",
    )

    applied = store.snapshots[snapshot.record.id]
    assert applied.execution.state is ExecutionState.NO_SIDE_EFFECT
    assert applied.delivery.state is expected_delivery


def test_receipt_timeout_marks_unknown_and_opens_incident_once() -> None:
    store = FakeReceiptStore()
    candidate = make_snapshot("timeout-synthetic", make_body())
    store.timeout_candidates.append(candidate)
    clock = FakeClock(RECEIPT_DUE_MS + 1)
    use_case = WatchReceiptTimeouts(store, clock, FakeIds())

    first = use_case.execute()
    second = use_case.execute()

    assert first.timed_out == 1
    assert second.timed_out == 0
    after = store.timeout_candidates[0]
    assert after.execution.state is ExecutionState.UNKNOWN
    assert after.delivery.state is DeliveryState.UNKNOWN
    assert store.incidents[-1]["incident_type"] == "UNKNOWN"
    assert store.incidents[-1]["severity"] == "HIGH"


def test_receipt_contract_is_strict() -> None:
    contract = jsonschema.Draft202012Validator(
        json.loads(Path("contracts/growth_engine/receipt.v2.schema.json").read_text())
    )
    assert contract.is_valid(make_body())
    assert not contract.is_valid({**make_body(), "unexpected": "field"})


def test_internal_receipt_route_authenticates_page_and_returns_receipt_ack() -> None:
    store = FakeReceiptStore()
    use_case = receiver(store)
    bearer = "synthetic-receipt-token"
    service_hash = hashlib.sha256(bearer.encode("utf-8")).hexdigest()
    container = SimpleNamespace(
        settings=SimpleNamespace(service_tokens=f"make-fb-hanoi:{service_hash}"),
        receive_receipt=use_case,
    )
    app: FastAPI = create_app(container)
    app.include_router(router)

    with TestClient(app) as client:
        response = client.post(
            "/internal/growth/v2/receipts",
            headers={"Authorization": f"Bearer {bearer}"},
            json=make_body(),
        )
        conflict_response = client.post(
            "/internal/growth/v2/receipts",
            headers={"Authorization": f"Bearer {bearer}"},
            json=make_body(post_id="post-synthetic-002"),
        )

    assert response.status_code == 200
    assert response.json()["accepted"] is True
    assert response.json()["duplicate"] is False
    assert len(store.jobs) == 1
    assert conflict_response.status_code == 409
    assert {incident["incident_type"] for incident in store.incidents} >= {"RECEIPT_CONFLICT", "DUPLICATE_POST"}


def test_internal_receipt_route_returns_503_when_inbox_storage_is_unavailable() -> None:
    class UnavailableStore(FakeReceiptStore):
        @contextmanager
        def begin_immediate(self) -> Iterator["FakeReceiptStore"]:
            raise ReceiptPersistenceUnavailable("synthetic storage outage")
            yield self

    bearer = "synthetic-receipt-token"
    service_hash = hashlib.sha256(bearer.encode("utf-8")).hexdigest()
    container = SimpleNamespace(
        settings=SimpleNamespace(service_tokens=f"make-fb-hanoi:{service_hash}"),
        receive_receipt=receiver(UnavailableStore()),
    )
    app: FastAPI = create_app(container)
    app.include_router(router)

    with TestClient(app) as client:
        response = client.post(
            "/internal/growth/v2/receipts",
            headers={"Authorization": f"Bearer {bearer}"},
            json=make_body(),
        )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ERR_GC2_DB_BUSY"
