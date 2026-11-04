from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from growth_engine.domain.delivery.states import DeliveryEvent, DeliveryState
from growth_engine.domain.publishing.backoff import full_jitter
from growth_engine.domain.publishing.command import CommandState, OutboxCommand, business_key
from growth_engine.domain.publishing.execution import Execution, ExecutionState
from growth_engine.domain.publishing.receipt import Receipt, ReceiptOutcome, is_placeholder_post_id
from growth_engine.domain.publishing.runtime_mode import PublishMode, RuntimeControls
from growth_engine.domain.publishing.window import PublishingPolicy, PublishWindow, grant_window
from growth_engine.domain.verification.verification import (
    VerificationEvidence,
    classify_verification,
)


# Dữ liệu test tự tạo; cần thay bằng fixture thật từ P0-T03/P0-T04.
SYNTHETIC_MARKER = {
    "_synthetic": True,
    "note": "cần thay bằng fixture thật từ P0-T03/P0-T04",
}


@pytest.fixture
def policy() -> PublishingPolicy:
    return PublishingPolicy(
        window_minutes=30,
        grant_ttl_seconds=60,
        receipt_grace_minutes=15,
        redeliver_after_ack_minutes=5,
        max_transport_attempts=8,
        verify_delay_minutes=5,
        unknown_escalation_minutes=60,
    )


def make_command(*, now_ms: int = 1_000, expires_at_ms: int = 9_000_000) -> OutboxCommand:
    assert SYNTHETIC_MARKER["_synthetic"] is True
    return OutboxCommand.new(
        command_id="cmd-synthetic-1",
        delivery_id="delivery-synthetic-1",
        revision_id="revision-synthetic-1",
        sequence_no=1,
        expires_at_ms=expires_at_ms,
        now_ms=now_ms,
        envelope_token="opaque-synthetic-envelope",
    )


def make_receipt(outcome: ReceiptOutcome, **overrides: object) -> Receipt:
    values: dict[str, object] = {
        "issuer": "make-test",
        "event_id": "event-synthetic-1",
        "execution_id": "execution-synthetic-1",
        "grant_id": "grant-synthetic-1",
        "command_id": "cmd-synthetic-1",
        "delivery_id": "delivery-synthetic-1",
        "revision_id": "revision-synthetic-1",
        "channel_id": "channel-synthetic-1",
        "remote_account_id": "account-synthetic-1",
        "payload_hash": "a" * 64,
        "outcome": outcome,
    }
    values.update(overrides)
    return Receipt(**values)  # type: ignore[arg-type]


def make_execution(policy: PublishingPolicy, state: ExecutionState = ExecutionState.AUTHORIZED) -> Execution:
    return Execution.authorize(
        execution_id="execution-synthetic-1",
        delivery_id="delivery-synthetic-1",
        command_id="cmd-synthetic-1",
        grant_id="grant-synthetic-1",
        now_ms=1_000,
        deadline_at_ms=100_000,
        policy=policy,
    )


def test_c01_create_command_and_business_key() -> None:
    command = make_command()
    assert command.state is CommandState.PENDING
    assert command.next_attempt_at_ms == 1_000
    assert command.attempts == 0
    assert business_key("delivery-1", "revision-2", 3) == "publish:delivery-1:revision-2:3"


def test_c02_claim_requires_pending_due_and_fences_old_lease() -> None:
    command = make_command().claim(now_ms=1_000, lease_token="lease-new", lease_ttl_ms=10_000)
    assert command.state is CommandState.DELIVERING
    assert command.lease_token == "lease-new"
    assert command.lease_expires_at_ms == 11_000
    with pytest.raises(ValueError):
        command.acknowledge(lease_token="lease-old", at_ms=2_000)

    not_due = make_command().claim(
        now_ms=1_000, lease_token="lease-1", lease_ttl_ms=10_000
    ).transport_failed(at_ms=1_000, rng=lambda low, high: high)
    with pytest.raises(ValueError):
        not_due.claim(now_ms=1_001, lease_token="lease", lease_ttl_ms=10_000)


def test_c03_acknowledge_requires_current_lease_token() -> None:
    command = make_command().claim(now_ms=1_000, lease_token="lease-1", lease_ttl_ms=1_000)
    acked = command.acknowledge(lease_token="lease-1", at_ms=1_500)
    assert acked.state is CommandState.ACKED
    assert acked.acked_at_ms == 1_500


def test_c04_transport_failure_uses_full_jitter_and_retry_after() -> None:
    command = make_command().claim(now_ms=1_000, lease_token="lease-1", lease_ttl_ms=10_000)
    pending = command.transport_failed(
        at_ms=2_000,
        rng=lambda low, high: high,
        retry_after_seconds=9,
    )
    assert pending.state is CommandState.PENDING
    assert pending.attempts == 1
    assert pending.next_attempt_at_ms == 11_000
    assert pending.lease_token is None

    exhausted = make_command(expires_at_ms=100_000)
    for attempt in range(8):
        exhausted = exhausted.claim(
            now_ms=exhausted.next_attempt_at_ms,
            lease_token=f"lease-{attempt}",
            lease_ttl_ms=1,
        ).transport_failed(at_ms=exhausted.next_attempt_at_ms, rng=lambda low, high: low)
    assert exhausted.attempts == 8
    with pytest.raises(ValueError):
        exhausted.claim(now_ms=exhausted.next_attempt_at_ms, lease_token="lease-last", lease_ttl_ms=1)


def test_c05_expired_lease_returns_to_pending() -> None:
    command = make_command().claim(now_ms=1_000, lease_token="lease-1", lease_ttl_ms=500)
    with pytest.raises(ValueError):
        command.recover_expired_lease(now_ms=1_499)
    recovered = command.recover_expired_lease(now_ms=1_500)
    assert recovered.state is CommandState.PENDING
    assert recovered.next_attempt_at_ms == 1_500
    assert recovered.lease_token is None


def test_c06_ack_redelivery_waits_and_preserves_envelope_and_token(policy: PublishingPolicy) -> None:
    acked = make_command().claim(now_ms=1_000, lease_token="lease-1", lease_ttl_ms=10_000).acknowledge(
        lease_token="lease-1", at_ms=2_000
    )
    with pytest.raises(ValueError):
        acked.redeliver_after_ack(now_ms=301_999, deadline_at_ms=1_000_000, policy=policy)
    redelivered = acked.redeliver_after_ack(now_ms=302_000, deadline_at_ms=1_000_000, policy=policy)
    assert redelivered.state is CommandState.PENDING
    assert redelivered.id == acked.id
    assert redelivered.envelope_token == acked.envelope_token
    assert redelivered.next_attempt_at_ms == 302_000
    with pytest.raises(ValueError):
        acked.redeliver_after_ack(now_ms=302_000, deadline_at_ms=421_999, policy=policy)


@pytest.mark.parametrize("state", [CommandState.PENDING, CommandState.DELIVERING, CommandState.ACKED])
def test_c07_authorize_closes_redelivery(state: CommandState) -> None:
    command = make_command()
    if state is CommandState.DELIVERING:
        command = command.claim(now_ms=1_000, lease_token="lease-1", lease_ttl_ms=10_000)
    elif state is CommandState.ACKED:
        command = command.claim(now_ms=1_000, lease_token="lease-1", lease_ttl_ms=10_000).acknowledge(
            lease_token="lease-1", at_ms=1_500
        )
    authorized = command.authorize()
    assert authorized.state is CommandState.AUTHORIZED
    with pytest.raises(ValueError):
        authorized.claim(now_ms=2_000, lease_token="lease-again", lease_ttl_ms=10_000)


@pytest.mark.parametrize("state", [CommandState.PENDING, CommandState.DELIVERING, CommandState.ACKED])
def test_c08_cancel_closes_open_command(state: CommandState) -> None:
    command = make_command()
    if state is CommandState.DELIVERING:
        command = command.claim(now_ms=1_000, lease_token="lease-1", lease_ttl_ms=10_000)
    elif state is CommandState.ACKED:
        command = command.claim(now_ms=1_000, lease_token="lease-1", lease_ttl_ms=10_000).acknowledge(
            lease_token="lease-1", at_ms=1_500
        )
    assert command.cancel().state is CommandState.CANCELLED


@pytest.mark.parametrize("state", [CommandState.PENDING, CommandState.DELIVERING, CommandState.ACKED])
def test_c09_expire_only_after_deadline(state: CommandState) -> None:
    command = make_command(expires_at_ms=2_000)
    if state is CommandState.DELIVERING:
        command = command.claim(now_ms=1_000, lease_token="lease-1", lease_ttl_ms=10_000)
    elif state is CommandState.ACKED:
        command = command.claim(now_ms=1_000, lease_token="lease-1", lease_ttl_ms=10_000).acknowledge(
            lease_token="lease-1", at_ms=1_500
        )
    with pytest.raises(ValueError):
        command.expire(now_ms=2_000)
    assert command.expire(now_ms=2_001).state is CommandState.EXPIRED


def test_e01_grant_window_is_clamped_to_deadline(policy: PublishingPolicy) -> None:
    grant = grant_window(now_ms=10_000, deadline_at_ms=30_000, ttl_seconds=60, receipt_grace_minutes=15)
    assert grant.grant_expires_at_ms == 30_000
    assert grant.receipt_due_at_ms == 930_000
    execution = make_execution(policy)
    assert execution.state is ExecutionState.AUTHORIZED
    assert execution.grant_expires_at_ms == 61_000
    assert execution.receipt_due_at_ms == 961_000


def test_e02_post_created_moves_authorized_to_reported(policy: PublishingPolicy) -> None:
    execution = make_execution(policy)
    reported = execution.accept_receipt(make_receipt(ReceiptOutcome.POST_CREATED, platform_post_id="123456"))
    assert reported.state is ExecutionState.REPORTED
    assert reported.platform_post_id == "123456"


def test_e03_rejected_receipt_requires_verified_error_class(policy: PublishingPolicy) -> None:
    execution = make_execution(policy)
    verified = execution.accept_receipt(
        make_receipt(ReceiptOutcome.REJECTED_NO_SIDE_EFFECT, error_class="VERIFIED_CLASS"),
        error_class_verified=True,
    )
    unverified = execution.accept_receipt(
        make_receipt(ReceiptOutcome.REJECTED_NO_SIDE_EFFECT, error_class="REQUIRED_FROM_P0"),
        error_class_verified=False,
    )
    assert verified.state is ExecutionState.NO_SIDE_EFFECT
    assert unverified.state is ExecutionState.UNKNOWN


def test_e04_unknown_timeout_and_outcome_move_to_unknown(policy: PublishingPolicy) -> None:
    execution = make_execution(policy)
    with pytest.raises(ValueError):
        execution.timeout(now_ms=execution.receipt_due_at_ms)
    assert execution.timeout(now_ms=execution.receipt_due_at_ms + 1).state is ExecutionState.UNKNOWN
    unknown = execution.accept_receipt(make_receipt(ReceiptOutcome.OUTCOME_UNKNOWN))
    assert unknown.state is ExecutionState.UNKNOWN


def test_e05_late_post_and_e06_operator_resolution(policy: PublishingPolicy) -> None:
    execution = make_execution(policy).timeout(now_ms=1_000_000)
    reported = execution.accept_receipt(make_receipt(ReceiptOutcome.POST_CREATED, platform_post_id="123456"))
    assert reported.state is ExecutionState.REPORTED
    with pytest.raises(ValueError):
        execution.resolve_no_side_effect(actor_id="operator", evidence="")
    resolved = execution.resolve_no_side_effect(actor_id="operator", evidence="history entry 42")
    assert resolved.state is ExecutionState.NO_SIDE_EFFECT


def test_e07_verification_mismatch_moves_reported_execution_to_unknown(policy: PublishingPolicy) -> None:
    reported = make_execution(policy).accept_receipt(
        make_receipt(ReceiptOutcome.POST_CREATED, platform_post_id="123456")
    )
    assert reported.verify_mismatch().state is ExecutionState.UNKNOWN


@pytest.mark.parametrize("value", ["", "null", "NULL", "{{1.id}}", "test_123", "  test_post  "])
def test_placeholder_post_ids_are_rejected(value: str) -> None:
    assert is_placeholder_post_id(value)
    with pytest.raises(ValueError):
        make_receipt(ReceiptOutcome.POST_CREATED, platform_post_id=value)


def test_receipt_rejects_unverified_shape_and_execution_mismatch(policy: PublishingPolicy) -> None:
    with pytest.raises(ValueError, match="error_class"):
        make_receipt(ReceiptOutcome.REJECTED_NO_SIDE_EFFECT)
    with pytest.raises(ValueError, match="execution grant"):
        make_execution(policy).accept_receipt(
            make_receipt(ReceiptOutcome.POST_CREATED, execution_id="another-execution", platform_post_id="123456")
        )


def test_full_jitter_is_bounded_and_rng_is_injected() -> None:
    assert full_jitter(0, lambda low, high: high) == 5
    assert full_jitter(5, lambda low, high: low) == 0
    assert full_jitter(20, lambda low, high: high) == 300
    with pytest.raises(ValueError):
        full_jitter(-1, lambda low, high: low)


def test_publish_window_and_policy_yaml(policy: PublishingPolicy) -> None:
    window = PublishWindow.for_scheduled(scheduled_at_ms=1_000, policy=policy)
    assert window.deadline_at_ms == 1_801_000
    assert window.is_open(1_000)
    assert window.is_open(window.deadline_at_ms)
    assert window.is_expired(window.deadline_at_ms + 1)

    config_path = Path("config/projects/venho_hotel/growth_engine/publishing_policy.yaml")
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert PublishingPolicy(**raw) == policy


@pytest.mark.parametrize(
    ("mode", "paused", "channel_enabled", "channel_paused", "expected"),
    [
        (PublishMode.LIVE_MANUAL, False, True, False, True),
        (PublishMode.DISABLED, False, True, False, False),
        (PublishMode.DRY_RUN, False, True, False, False),
        (PublishMode.LIVE_MANUAL, True, True, False, False),
        (PublishMode.LIVE_MANUAL, False, False, False, False),
        (PublishMode.LIVE_MANUAL, False, True, True, False),
    ],
)
def test_runtime_controls_require_live_unpaused_current_epoch(
    mode: PublishMode,
    paused: bool,
    channel_enabled: bool,
    channel_paused: bool,
    expected: bool,
) -> None:
    controls = RuntimeControls(mode=mode, dispatch_epoch="epoch-1", global_pause=paused)
    assert controls.can_dispatch(
        expected_epoch="epoch-1",
        channel_enabled=channel_enabled,
        channel_paused=channel_paused,
    ) is expected
    if expected:
        assert not controls.can_dispatch(expected_epoch="old-epoch")


def test_verification_classification_emits_only_definitive_events() -> None:
    assert classify_verification(
        VerificationEvidence(
            delivery_state=DeliveryState.REPORTED_PUBLISHED,
            existence="EXISTS",
            ownership="MATCH",
        )
    ) is DeliveryEvent.VERIFY_OK
    for existence in ("NOT_FOUND", "MISMATCH"):
        assert classify_verification(
            VerificationEvidence(
                delivery_state=DeliveryState.REPORTED_PUBLISHED,
                existence=existence,
                ownership="UNKNOWN",
            )
        ) is DeliveryEvent.VERIFY_MISMATCH
    assert classify_verification(
        VerificationEvidence(
            delivery_state=DeliveryState.REPORTED_PUBLISHED,
            existence="UNAVAILABLE",
            ownership="UNKNOWN",
        )
    ) is None
    assert classify_verification(
        VerificationEvidence(
            delivery_state=DeliveryState.PUBLISHED,
            existence="EXISTS",
            ownership="MATCH",
            previous_visibility="VISIBLE",
            observed_visibility="DELETED",
        )
    ) is DeliveryEvent.VISIBILITY_CHANGE
    assert classify_verification(
        VerificationEvidence(
            delivery_state=DeliveryState.PUBLISHED,
            existence="UNAVAILABLE",
            ownership="UNKNOWN",
            previous_visibility="VISIBLE",
            observed_visibility="VISIBLE",
        )
    ) is None
