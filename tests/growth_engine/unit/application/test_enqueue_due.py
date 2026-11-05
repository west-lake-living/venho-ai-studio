from __future__ import annotations

import fcntl
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator
from zoneinfo import ZoneInfo

from growth_engine.adapters.inbound.workers.publish_lane import (
    PublishLane,
    build_publish_tasks,
)
from growth_engine.application.publishing.enqueue_due import (
    EnqueueCandidate,
    EnqueueDue,
)
from growth_engine.application.publishing.expire_overdue import (
    ExpireCandidate,
    ExpireOverdue,
)
from growth_engine.domain.channels.channel import Channel, ChannelConfig, ChannelPlatform, config_hash
from growth_engine.domain.delivery.approval import ApprovalDecision, ApprovalType
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.revision import DeliveryRevision
from growth_engine.domain.delivery.states import DeliveryState
from growth_engine.domain.publishing.command import OutboxCommand
from growth_engine.domain.publishing.runtime_mode import PublishMode, RuntimeControls


SYNTHETIC_FIXTURE_NOTE = "cần thay bằng fixture thật từ P0-T03/P0-T04"


class FakeIds:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._value = 0

    def new_id(self) -> str:
        with self._lock:
            self._value += 1
            return f"synthetic-{self._value}"


class FakeTokens:
    def __init__(self) -> None:
        self.claims = []

    def issue(self, claims) -> str:
        self.claims.append(claims)
        return f"synthetic-token:{claims.command_id}:{claims.expires_at_ms}"


class FakeStore:
    def __init__(self, controls: RuntimeControls, candidates: list[EnqueueCandidate]) -> None:
        self.controls = controls
        self.candidates = {candidate.delivery.id: candidate for candidate in candidates}
        self.commands: dict[str, OutboxCommand] = {}
        self.expired_commands: set[str] = set()
        self.open_command_ids: set[str] = set()
        self.audit: list[tuple[str, str]] = []
        self._lock = threading.RLock()

    def read_controls(self) -> RuntimeControls:
        return self.controls

    def due_approved(self, now_ms: int, limit: int) -> tuple[str, ...]:
        due = []
        for delivery_id, candidate in self.candidates.items():
            scheduled_at = candidate.revision.payload["scheduled_at_ms"]
            if candidate.delivery.state is DeliveryState.APPROVED and scheduled_at <= now_ms:
                due.append(delivery_id)
        return tuple(sorted(due)[:limit])

    def overdue_delivery_ids(self, now_ms: int) -> tuple[str, ...]:
        overdue = []
        for delivery_id, candidate in self.candidates.items():
            if candidate.revision.payload["deadline_at_ms"] < now_ms and candidate.delivery.state in {
                DeliveryState.DRAFT,
                DeliveryState.IN_REVIEW,
                DeliveryState.APPROVED,
                DeliveryState.QUEUED,
                DeliveryState.BLOCKED,
            }:
                overdue.append(delivery_id)
        return tuple(sorted(overdue))

    @contextmanager
    def begin_immediate(self) -> Iterator["FakeStore"]:
        with self._lock:
            yield self

    def current_controls(self) -> RuntimeControls:
        return self.controls

    def get_enqueue_candidate(self, delivery_id: str) -> EnqueueCandidate | None:
        return self.candidates.get(delivery_id)

    def commit_enqueue(
        self,
        candidate: EnqueueCandidate,
        command: OutboxCommand,
        updated_delivery: Delivery,
        *,
        expected_row_version: int,
        dispatch_epoch: str,
        at_ms: int,
        audit_event_id: str,
        correlation_id: str,
    ) -> bool:
        current = self.candidates.get(candidate.delivery.id)
        if current is None or current.delivery.row_version != expected_row_version:
            return False
        if command.business_key in {item.business_key for item in self.commands.values()}:
            return False
        self.commands[command.id] = command
        self.candidates[candidate.delivery.id] = EnqueueCandidate(
            **{**candidate.__dict__, "delivery": updated_delivery}
        )
        self.audit.append((candidate.delivery.id, correlation_id))
        return True

    def get_expire_candidate(self, delivery_id: str) -> ExpireCandidate | None:
        candidate = self.candidates.get(delivery_id)
        if candidate is None:
            return None
        return ExpireCandidate(
            delivery=candidate.delivery,
            deadline_at_ms=candidate.revision.payload["deadline_at_ms"],
            has_live_execution=False,
        )

    def commit_expire(
        self,
        candidate: ExpireCandidate,
        updated_delivery: Delivery,
        *,
        expected_row_version: int,
        at_ms: int,
        audit_event_id: str,
        correlation_id: str,
    ) -> bool:
        existing = self.candidates[candidate.delivery.id]
        if existing.delivery.row_version != expected_row_version:
            return False
        self.candidates[candidate.delivery.id] = EnqueueCandidate(
            **{**existing.__dict__, "delivery": updated_delivery}
        )
        if candidate.delivery.id in self.open_command_ids:
            self.expired_commands.add(candidate.delivery.id)
            self.open_command_ids.remove(candidate.delivery.id)
        self.audit.append((candidate.delivery.id, correlation_id))
        return True


def make_candidate(
    delivery_id: str,
    *,
    channel_key: str = "page-a",
    paused: bool = False,
    state: DeliveryState = DeliveryState.APPROVED,
    scheduled_at_ms: int = 1_000,
    deadline_at_ms: int = 10_000,
    remote_account_id: str | None = None,
    platform: ChannelPlatform = ChannelPlatform.FACEBOOK,
) -> EnqueueCandidate:
    channel_id = f"channel-{channel_key}"
    remote_id = remote_account_id or f"remote-{channel_key}"
    config = ChannelConfig(
        id=f"config-{channel_key}",
        channel_id=channel_id,
        version=1,
        make_route_ref=f"route-{channel_key}",
        graph_api_version="REQUIRED_FROM_P0",
        capability={"_synthetic": True, "note": SYNTHETIC_FIXTURE_NOTE},
    )
    channel = Channel(
        id=channel_id,
        project_id="venho_hotel",
        environment="test",
        channel_key=channel_key,
        platform=platform,
        remote_account_id=remote_id,
        name=channel_key,
        enabled=True,
        paused=paused,
    )
    revision_id = f"revision-{delivery_id}"
    revision = DeliveryRevision.create(
        {
            "delivery_id": delivery_id,
            "revision_id": revision_id,
            "channel_id": channel_id,
            "remote_account_id": remote_id,
            "channel_config_hash": config_hash(config),
            "caption": "Approved synthetic caption",
            "media": [{"sha256": "a" * 64, "mime": "image/jpeg", "width": 1080, "height": 1350}],
            "scheduled_at_ms": scheduled_at_ms,
            "deadline_at_ms": deadline_at_ms,
            "qc_report_id": "qc-synthetic",
            "ruleset_hash": "b" * 64,
            "fact_snapshot_hash": "c" * 64,
        }
    )
    approval = ApprovalDecision(
        id=f"approval-{delivery_id}",
        revision_id=revision_id,
        payload_hash=revision.payload_hash,
        decision=ApprovalType.APPROVE,
        actor_id="synthetic-editor",
        created_at_ms=500,
    )
    return EnqueueCandidate(
        delivery=Delivery(delivery_id, state),
        current_revision_id=revision_id,
        active_approval_id=approval.id,
        revision=revision,
        approval=approval,
        approval_revoked=False,
        channel=channel,
        channel_config=config,
    )


def test_two_concurrent_ticks_enqueue_one_command() -> None:
    # Synthetic fixture only; cần thay bằng fixture thật từ P0-T03/P0-T04.
    store = FakeStore(
        RuntimeControls(PublishMode.LIVE_MANUAL, "epoch-1"),
        [make_candidate("delivery-a")],
    )
    tokens = FakeTokens()
    use_case = EnqueueDue(store, tokens, FakeIds())

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: use_case.execute(2_000), range(2)))

    assert sum(len(result.enqueued_delivery_ids) for result in results) == 1
    assert len(store.commands) == 1
    assert store.candidates["delivery-a"].delivery.state is DeliveryState.QUEUED
    assert tokens.claims[0].audience == "make-route:channel-page-a"
    assert tokens.claims[0].dispatch_epoch == "epoch-1"


def test_server_start_after_window_expires_0900_delivery_without_enqueue() -> None:
    # Synthetic 09:00 → 09:30 ICT window with the server starting at 09:40.
    ict = ZoneInfo("Asia/Ho_Chi_Minh")
    scheduled_at_ms = int(datetime(2026, 11, 4, 9, 0, tzinfo=ict).timestamp() * 1000)
    deadline_at_ms = int(datetime(2026, 11, 4, 9, 30, tzinfo=ict).timestamp() * 1000)
    now_ms = int(datetime(2026, 11, 4, 9, 40, tzinfo=ict).timestamp() * 1000)
    candidate = make_candidate(
        "missed-0900",
        state=DeliveryState.APPROVED,
        scheduled_at_ms=scheduled_at_ms,
        deadline_at_ms=deadline_at_ms,
    )
    store = FakeStore(RuntimeControls(PublishMode.LIVE_MANUAL, "epoch-1"), [candidate])

    enqueue = EnqueueDue(store, FakeTokens(), FakeIds()).execute(now_ms)
    expired = ExpireOverdue(store, FakeIds()).execute(now_ms)

    assert enqueue.enqueued_delivery_ids == ()
    assert expired.expired_delivery_ids == ("missed-0900",)
    assert store.candidates["missed-0900"].delivery.state is DeliveryState.EXPIRED
    assert not store.commands


def test_expiring_queued_delivery_closes_its_open_command() -> None:
    candidate = make_candidate("queued-a", state=DeliveryState.QUEUED, deadline_at_ms=1_500)
    store = FakeStore(RuntimeControls(PublishMode.LIVE_MANUAL, "epoch-1"), [candidate])
    store.open_command_ids.add("queued-a")

    result = ExpireOverdue(store, FakeIds()).execute(2_000)

    assert result.expired_delivery_ids == ("queued-a",)
    assert store.candidates["queued-a"].delivery.state is DeliveryState.EXPIRED
    assert store.expired_commands == {"queued-a"}


def test_dry_run_never_enqueues_a_command() -> None:
    store = FakeStore(
        RuntimeControls(PublishMode.DRY_RUN, "epoch-1"),
        [make_candidate("delivery-a")],
    )

    result = EnqueueDue(store, FakeTokens(), FakeIds()).execute(2_000)

    assert result.skipped_reason == "MODE_NOT_LIVE_MANUAL"
    assert not store.commands
    assert store.candidates["delivery-a"].delivery.state is DeliveryState.APPROVED


def test_paused_page_b_is_skipped_while_page_a_is_enqueued() -> None:
    store = FakeStore(
        RuntimeControls(PublishMode.LIVE_MANUAL, "epoch-1"),
        [make_candidate("delivery-a", channel_key="page-a"), make_candidate("delivery-b", channel_key="page-b", paused=True)],
    )

    result = EnqueueDue(store, FakeTokens(), FakeIds()).execute(2_000)

    assert result.enqueued_delivery_ids == ("delivery-a",)
    assert store.candidates["delivery-a"].delivery.state is DeliveryState.QUEUED
    assert store.candidates["delivery-b"].delivery.state is DeliveryState.APPROVED
    assert len(store.commands) == 1


def test_instagram_delivery_is_eligible_for_publish_command() -> None:
    candidate = make_candidate(
        "delivery-ig",
        channel_key="ig_venho",
        platform=ChannelPlatform.INSTAGRAM,
    )
    store = FakeStore(RuntimeControls(PublishMode.LIVE_MANUAL, "epoch-1"), [candidate])

    result = EnqueueDue(store, FakeTokens(), FakeIds()).execute(2_000)

    assert result.enqueued_delivery_ids == ("delivery-ig",)
    assert len(store.commands) == 1


def test_publish_lane_second_instance_returns_75_and_logs_lock() -> None:
    messages: list[str] = []
    class NoopLoop:
        def run_forever(self) -> None:
            raise AssertionError("a locked lane must not start its loop")

    with tempfile.TemporaryDirectory() as temp_dir:
        lock_path = Path(temp_dir) / "state" / "publish.lock"
        lock_path.parent.mkdir()
        with lock_path.open("a+") as held_lock:
            fcntl.flock(held_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            lane = PublishLane(NoopLoop(), lock_path, log_error=messages.append)
            assert lane.run_forever() == 75

    assert messages and "already running" in messages[0].lower()


def test_publish_lane_ticks_enqueue_every_30s_and_expire_every_60s() -> None:
    calls: list[str] = []
    tasks = build_publish_tasks(
        {
            "enqueue_due": lambda: calls.append("enqueue"),
            "expire_overdue": lambda: calls.append("expire"),
            "dispatch_outbox": lambda: calls.append("dispatch"),
            "notifications": lambda: calls.append("notifications"),
            "apply_receipts": lambda: calls.append("apply-receipts"),
            "receipt_timeouts": lambda: calls.append("receipt-timeouts"),
        }
    )
    by_name = {task.name: task for task in tasks}

    assert by_name["enqueue-due"].interval_s == 30
    assert by_name["expire-overdue"].interval_s == 60
    assert by_name["dispatch-outbox"].interval_s == 5
    assert by_name["notifications"].interval_s == 5
    assert by_name["apply-receipts"].interval_s == 5
    assert by_name["receipt-timeouts"].interval_s == 60
    by_name["enqueue-due"].fn()
    by_name["expire-overdue"].fn()
    by_name["dispatch-outbox"].fn()
    by_name["notifications"].fn()
    by_name["apply-receipts"].fn()
    by_name["receipt-timeouts"].fn()
    assert calls == ["enqueue", "expire", "dispatch", "notifications", "apply-receipts", "receipt-timeouts"]
