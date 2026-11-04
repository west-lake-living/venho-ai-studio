from __future__ import annotations

from tests.growth_engine.fault.test_crash_points import _envelope
from tests.growth_engine.support.fake_make import FakeAuthorizeEndpoint, FakeMake, FakeReceiptEndpoint


def test_approved_content_posts_once_to_both_pages() -> None:
    fake_make = FakeMake()
    authorize = FakeAuthorizeEndpoint()
    receipts = FakeReceiptEndpoint()
    page_a = _envelope("command-page-a", "delivery-page-a")
    page_b = _envelope("command-page-b", "delivery-page-b")
    page_a["remote_page_id"] = "page-a"
    page_b["remote_page_id"] = "page-b"

    result_a = fake_make.deliver(page_a, authorize=authorize, receipt=receipts)
    result_b = fake_make.deliver(page_b, authorize=authorize, receipt=receipts)

    assert result_a["result"] == result_b["result"] == "POST_CREATED"
    assert result_a["caption_hash"] == result_b["caption_hash"] == "b" * 64
    assert result_a["media_sha256"] == result_b["media_sha256"] == "c" * 64
    assert result_a["page_id"] != result_b["page_id"]
    assert fake_make.mutation_counter == {"delivery-page-a": 1, "delivery-page-b": 1}
