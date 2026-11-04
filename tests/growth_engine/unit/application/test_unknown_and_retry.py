from __future__ import annotations

from contextlib import contextmanager

import pytest

from growth_engine.application.verification.close_delivery import CloseDelivery
from growth_engine.application.verification.request_safe_retry import (
    RequestSafeRetry,
    SafeRetryCandidate,
)
from growth_engine.application.verification.resolve_unknown import (
    ResolveUnknown,
    UnknownCandidate,
    UnknownEvidence,
)
from growth_engine.domain.channels.channel import ChannelConfig
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.states import DeliveryState
from growth_engine.domain.publishing.command import OutboxCommand
from growth_engine.domain.publishing.execution import Execution, ExecutionState


class Clock:
    def now_ms(self) -> int:
        return 1_800_000_000_000


class Ids:
    def __init__(self) -> None:
        self.index = 0

    def new_id(self) -> str:
        self.index += 1
        return f"synthetic-id-{self.index}"


def _config() -> ChannelConfig:
    return ChannelConfig(
        id="synthetic-config",
        channel_id="synthetic-channel",
        version=1,
        make_route_ref="GE_MAKE_WEBHOOK_URL_SYNTHETIC",
        graph_api_version="v-synthetic",
        capability={"_synthetic": True, "note": "cần thay bằng fixture thật từ P0-T03/P0-T04"},
    )


def _execution(state: ExecutionState) -> Execution:
    return Execution(
        "synthetic-execution", "synthetic-delivery", "synthetic-command", "synthetic-grant",
        state, 1_800_000_060_000, 1_800_000_900_000,
        "synthetic-post" if state is ExecutionState.REPORTED else None,
    )


class ResolveTx:
    def __init__(self, candidate: UnknownCandidate) -> None:
        self.candidate = candidate
        self.saved = None

    def get_candidate(self, delivery_id: str):
        return self.candidate if delivery_id == self.candidate.delivery.id else None

    def commit_resolution(self, candidate, **values):
        self.saved = values
        return True


class ResolveStore:
    def __init__(self, candidate: UnknownCandidate) -> None:
        self.tx = ResolveTx(candidate)

    @contextmanager
    def begin_immediate(self):
        yield self.tx


class Reader:
    def __init__(self, ownership: str = "MATCH") -> None:
        self.ownership = ownership

    def read_post(self, **kwargs):
        return type("Result", (), {"existence": "EXISTS", "ownership": self.ownership})()

    def read_permalink(self, permalink: str, **kwargs):
        assert permalink.startswith("https://synthetic.example.invalid/")
        return "synthetic-post-found", self.read_post(**kwargs)


def _unknown_candidate() -> UnknownCandidate:
    return UnknownCandidate(
        delivery=Delivery("synthetic-delivery", DeliveryState.UNKNOWN),
        execution=_execution(ExecutionState.UNKNOWN),
        channel_id="synthetic-channel",
        remote_page_id="synthetic-page",
        revision_id="synthetic-revision",
        payload_hash="a" * 64,
        expected_caption="synthetic caption",
        channel_config=_config(),
    )


def test_unknown_has_no_direct_safe_retry_path() -> None:
    candidate = SafeRetryCandidate(
        Delivery("synthetic-delivery", DeliveryState.UNKNOWN),
        "synthetic-revision", Clock().now_ms() + 600_000, 1,
        (ExecutionState.NO_SIDE_EFFECT,), False, True, False,
    )
    retry = RequestSafeRetry(SafeRetryStore(candidate), CommandFactory(), Clock(), Ids())

    with pytest.raises(ValueError, match="only for a BLOCKED"):
        retry.execute(
            "synthetic-delivery", expected_row_version=1, actor_id="synthetic-actor", reason="synthetic reason"
        )


def test_resolve_post_found_verifies_page_then_moves_to_reported() -> None:
    candidate = _unknown_candidate()
    store = ResolveStore(candidate)
    result = ResolveUnknown(store, Reader(), Clock(), Ids()).execute(
        candidate.delivery.id,
        UnknownEvidence("POST_FOUND", "synthetic-actor", "found on Page", platform_post_id="synthetic-post-found"),
    )

    assert result.outcome == "RESOLVED_PUBLISHED"
    assert result.delivery_state is DeliveryState.REPORTED_PUBLISHED
    assert store.tx.saved["updated_execution"].state is ExecutionState.REPORTED
    assert store.tx.saved["post_id"] == "synthetic-post-found"


def test_resolve_post_found_can_verify_operator_permalink() -> None:
    candidate = _unknown_candidate()
    store = ResolveStore(candidate)
    result = ResolveUnknown(store, Reader(), Clock(), Ids()).execute(
        candidate.delivery.id,
        UnknownEvidence(
            "POST_FOUND", "synthetic-actor", "found on the target Page",
            permalink="https://synthetic.example.invalid/post/123",
        ),
    )

    assert result.delivery_state is DeliveryState.REPORTED_PUBLISHED
    assert store.tx.saved["post_id"] == "synthetic-post-found"


def test_ambiguous_or_wrong_page_evidence_does_not_resolve_unknown() -> None:
    candidate = _unknown_candidate()
    store = ResolveStore(candidate)

    with pytest.raises(ValueError, match="does not verify"):
        ResolveUnknown(store, Reader("MISMATCH"), Clock(), Ids()).execute(
            candidate.delivery.id,
            UnknownEvidence("POST_FOUND", "synthetic-actor", "maybe same post", platform_post_id="synthetic-post"),
        )
    assert store.tx.saved is None


def test_no_side_effect_requires_evidence_and_moves_to_blocked() -> None:
    candidate = _unknown_candidate()
    store = ResolveStore(candidate)
    result = ResolveUnknown(store, Reader(), Clock(), Ids()).execute(
        candidate.delivery.id,
        UnknownEvidence(
            "NO_SIDE_EFFECT", "synthetic-actor", "Make stopped before create", make_execution_ref="synthetic-make-run"
        ),
    )

    assert result.delivery_state is DeliveryState.BLOCKED
    assert store.tx.saved["updated_execution"].state is ExecutionState.NO_SIDE_EFFECT


class SafeRetryTx:
    def __init__(self, candidate: SafeRetryCandidate) -> None:
        self.candidate = candidate
        self.saved = None

    def get_candidate(self, _delivery_id: str):
        return self.candidate

    def commit_safe_retry(self, candidate, **values):
        self.saved = values
        return True


class SafeRetryStore:
    def __init__(self, candidate: SafeRetryCandidate) -> None:
        self.tx = SafeRetryTx(candidate)

    @contextmanager
    def begin_immediate(self):
        yield self.tx


class CommandFactory:
    def create(self, candidate: SafeRetryCandidate, sequence_no: int, now_ms: int) -> OutboxCommand:
        return OutboxCommand.new(
            command_id=f"synthetic-retry-{sequence_no}",
            delivery_id=candidate.delivery.id,
            revision_id=candidate.current_revision_id,
            sequence_no=sequence_no,
            expires_at_ms=candidate.deadline_at_ms,
            now_ms=now_ms,
            envelope_token="synthetic-token",
        )


def _safe_candidate(
    *,
    states: tuple[ExecutionState, ...] = (ExecutionState.NO_SIDE_EFFECT,),
    approved: bool = True,
    revoked: bool = False,
) -> SafeRetryCandidate:
    return SafeRetryCandidate(
        Delivery("synthetic-delivery", DeliveryState.BLOCKED, row_version=4),
        "synthetic-revision", Clock().now_ms() + 600_000, 1, states, False, approved, revoked,
    )


def test_safe_retry_increments_sequence_only_after_no_side_effect() -> None:
    candidate = _safe_candidate()
    store = SafeRetryStore(candidate)
    result = RequestSafeRetry(store, CommandFactory(), Clock(), Ids()).execute(
        candidate.delivery.id,
        expected_row_version=4,
        actor_id="synthetic-actor",
        reason="verified no post was created",
    )

    assert result.sequence_no == 2
    assert result.business_key == "publish:synthetic-delivery:synthetic-revision:2"
    assert store.tx.saved["updated_delivery"].state is DeliveryState.QUEUED


@pytest.mark.parametrize(
    ("states", "approved", "revoked", "message"),
    [
        ((ExecutionState.UNKNOWN,), True, False, "NO_SIDE_EFFECT"),
        ((ExecutionState.NO_SIDE_EFFECT,), False, False, "approval"),
        ((ExecutionState.NO_SIDE_EFFECT,), True, True, "approval"),
    ],
)
def test_safe_retry_refuses_ambiguous_or_revoked_history(states, approved, revoked, message) -> None:
    candidate = _safe_candidate(states=states, approved=approved, revoked=revoked)
    service = RequestSafeRetry(SafeRetryStore(candidate), CommandFactory(), Clock(), Ids())

    with pytest.raises(ValueError, match=message):
        service.execute(
            candidate.delivery.id, expected_row_version=4, actor_id="synthetic-actor", reason="synthetic reason"
        )


class CloseTx:
    def __init__(self, delivery: Delivery, live: bool = False) -> None:
        self.delivery = delivery
        self.live = live
        self.saved = None

    def get_delivery(self, _delivery_id: str):
        return self.delivery

    def has_live_execution(self, _delivery_id: str) -> bool:
        return self.live

    def commit_close(self, delivery, **values):
        self.saved = values
        return True


class CloseStore:
    def __init__(self, delivery: Delivery, live: bool = False) -> None:
        self.tx = CloseTx(delivery, live)

    @contextmanager
    def begin_immediate(self):
        yield self.tx


def test_close_delivery_requires_actor_reason_and_no_live_execution() -> None:
    delivery = Delivery("synthetic-delivery", DeliveryState.BLOCKED, row_version=2)
    store = CloseStore(delivery)
    result = CloseDelivery(store, Clock(), Ids()).execute(
        delivery.id, expected_row_version=2, actor_id="synthetic-actor", reason="deadline passed"
    )
    assert result.state is DeliveryState.FAILED_FINAL

    live_store = CloseStore(delivery, live=True)
    with pytest.raises(ValueError, match="live execution"):
        CloseDelivery(live_store, Clock(), Ids()).execute(
            delivery.id, expected_row_version=2, actor_id="synthetic-actor", reason="close"
        )
