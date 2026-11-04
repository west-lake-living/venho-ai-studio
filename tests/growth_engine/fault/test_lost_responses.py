from __future__ import annotations

import pytest

from tests.growth_engine.fault.test_crash_points import _envelope
from tests.growth_engine.support.fake_make import (
    AFTER_AUTHORIZE_COMMIT,
    FakeAuthorizeEndpoint,
    FakeMake,
    FakeReceiptEndpoint,
    InjectedCrash,
)


def test_lost_authorize_response_becomes_no_second_grant_or_post() -> None:
    fake_make = FakeMake()
    authorize = FakeAuthorizeEndpoint()
    receipts = FakeReceiptEndpoint()
    envelope = _envelope()

    with pytest.raises(InjectedCrash):
        fake_make.deliver(
            envelope, authorize=authorize, receipt=receipts, crash_at=AFTER_AUTHORIZE_COMMIT
        )
    retry = fake_make.deliver(envelope, authorize=authorize, receipt=receipts)

    assert retry["result"] == "ALREADY_AUTHORIZED"
    assert len(authorize.grants_by_command) == 1
    assert fake_make.mutation_counter["delivery-1"] == 0


def test_page_b_error_and_recovery_never_reposts_page_a() -> None:
    fake_make = FakeMake()
    authorize = FakeAuthorizeEndpoint(rejected_pages={"page-b"})
    receipts = FakeReceiptEndpoint()
    page_a = _envelope("command-a", "delivery-a")
    page_a["remote_page_id"] = "page-a"
    page_b = _envelope("command-b", "delivery-b")
    page_b["remote_page_id"] = "page-b"

    fake_make.deliver(page_a, authorize=authorize, receipt=receipts)
    failed_b = fake_make.deliver(page_b, authorize=authorize, receipt=receipts)
    authorize.rejected_pages.clear()
    recovered_b = fake_make.deliver(page_b, authorize=authorize, receipt=receipts)

    assert failed_b["result"] == "PAGE_REJECTED"
    assert recovered_b["result"] == "POST_CREATED"
    assert fake_make.mutation_counter["delivery-a"] == 1
    assert fake_make.mutation_counter["delivery-b"] == 1
    assert sum(fake_make.mutation_counter.values()) == 2
