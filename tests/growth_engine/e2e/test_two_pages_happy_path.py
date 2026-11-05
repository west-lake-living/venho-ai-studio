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
    page_a["channel_key"] = "fb_hanoi"
    page_b["remote_page_id"] = "page-b"
    page_b["channel_key"] = "fb_venho"

    result_a = fake_make.deliver(page_a, authorize=authorize, receipt=receipts)
    result_b = fake_make.deliver(page_b, authorize=authorize, receipt=receipts)

    assert result_a["result"] == result_b["result"] == "POST_CREATED"
    assert result_a["caption_hash"] == result_b["caption_hash"] == "b" * 64
    assert result_a["media_sha256"] == result_b["media_sha256"] == "c" * 64
    assert result_a["page_id"] != result_b["page_id"]
    assert fake_make.mutation_counter == {"delivery-page-a": 1, "delivery-page-b": 1}
    assert fake_make.route_by_command == {
        "command-page-a": "facebook_hanoi",
        "command-page-b": "facebook_venho",
    }


def test_fake_make_routes_one_command_to_each_of_three_platform_branches() -> None:
    fake_make = FakeMake()
    authorize = FakeAuthorizeEndpoint()
    receipts = FakeReceiptEndpoint()
    commands = [
        {**_envelope("cmd-hanoi", "delivery-hanoi"), "channel_key": "fb_hanoi", "platform": "facebook"},
        {**_envelope("cmd-venho", "delivery-venho"), "channel_key": "fb_venho", "platform": "facebook"},
        {**_envelope("cmd-ig", "delivery-ig"), "channel_key": "ig_venho", "platform": "instagram"},
    ]

    results = [fake_make.deliver(item, authorize=authorize, receipt=receipts) for item in commands]

    assert [result["result"] for result in results] == ["POST_CREATED"] * 3
    assert results[2]["post_id"].startswith("fake-media-")
    assert fake_make.route_by_command == {
        "cmd-hanoi": "facebook_hanoi",
        "cmd-venho": "facebook_venho",
        "cmd-ig": "instagram_venho",
    }
    assert fake_make.mutation_counter == {
        "delivery-hanoi": 1,
        "delivery-venho": 1,
        "delivery-ig": 1,
    }
