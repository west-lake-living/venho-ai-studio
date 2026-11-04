from __future__ import annotations

from tests.growth_engine.fault.test_crash_points import _envelope
from tests.growth_engine.support.fake_make import FakeAuthorizeEndpoint, FakeMake, FakeReceiptEndpoint


def test_duplicate_webhook_reuses_authorization_without_second_post() -> None:
    fake_make = FakeMake()
    authorize = FakeAuthorizeEndpoint()
    receipts = FakeReceiptEndpoint()
    envelope = _envelope()

    first = fake_make.deliver(envelope, authorize=authorize, receipt=receipts)
    duplicate = fake_make.deliver(envelope, authorize=authorize, receipt=receipts)

    assert first["post_id"] == fake_make.posts_by_command["command-1"]["post_id"]
    assert duplicate["result"] == "ALREADY_AUTHORIZED"
    assert fake_make.mutation_counter["delivery-1"] == 1
    assert sum(receipts.apply_count.values()) == 1


def test_lost_ack_after_send_does_not_duplicate_post() -> None:
    fake_make = FakeMake()
    authorize = FakeAuthorizeEndpoint()
    receipts = FakeReceiptEndpoint()
    envelope = _envelope()

    fake_make.deliver(envelope, authorize=authorize, receipt=receipts)
    # The caller loses the HTTP response and retries the same webhook envelope.
    retry = fake_make.deliver(envelope, authorize=authorize, receipt=receipts)

    assert retry["result"] == "ALREADY_AUTHORIZED"
    assert fake_make.mutation_counter["delivery-1"] == 1
