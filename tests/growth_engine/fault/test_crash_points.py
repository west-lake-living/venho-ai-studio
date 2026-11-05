from __future__ import annotations

import pytest

from tests.growth_engine.support.fake_make import (
    AFTER_AUTHORIZE_COMMIT,
    AFTER_POST_CREATE,
    AFTER_RECEIPT_APPLY,
    FakeAuthorizeEndpoint,
    FakeMake,
    FakeReceiptEndpoint,
    InjectedCrash,
)


def _envelope(command_id: str = "command-1", delivery_id: str = "delivery-1") -> dict[str, object]:
    return {
        "command_id": command_id,
        "delivery_id": delivery_id,
        "channel_key": "fb_hanoi",
        "platform": "facebook",
        "remote_page_id": "page-test-a",
        "payload_hash": "a" * 64,
        "caption_hash": "b" * 64,
        "media_sha256": "c" * 64,
    }


def test_outbox_commit_crash_before_send_has_no_side_effect() -> None:
    fake_make = FakeMake()
    envelope = _envelope()
    outbox_committed = True
    assert outbox_committed
    assert fake_make.mutation_counter["delivery-1"] == 0

    authorize = FakeAuthorizeEndpoint()
    receipts = FakeReceiptEndpoint()
    fake_make.deliver(envelope, authorize=authorize, receipt=receipts)
    assert fake_make.mutation_counter["delivery-1"] == 1


@pytest.mark.parametrize("crash_at", [AFTER_AUTHORIZE_COMMIT, AFTER_POST_CREATE, AFTER_RECEIPT_APPLY])
def test_injected_crash_points_never_mutate_same_delivery_twice(crash_at: str) -> None:
    fake_make = FakeMake()
    authorize = FakeAuthorizeEndpoint()
    receipts = FakeReceiptEndpoint()
    envelope = _envelope()

    with pytest.raises(InjectedCrash):
        fake_make.deliver(envelope, authorize=authorize, receipt=receipts, crash_at=crash_at)
    fake_make.deliver(envelope, authorize=authorize, receipt=receipts)

    assert fake_make.mutation_counter["delivery-1"] <= 1
    assert len(fake_make.posts_by_command) <= 1
    assert max(receipts.apply_count.values(), default=0) <= 1
