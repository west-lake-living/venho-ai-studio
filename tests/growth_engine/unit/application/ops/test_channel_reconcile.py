from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

from growth_engine.application.ops.channel_reconcile import (
    Channel,
    ChannelPost,
    ChannelReconcileStatus,
    RegistryEntry,
    ScheduledSlot,
    load_registry_with_retries,
    reconcile_channels,
    select_new_alerts,
)


_SYNTHETIC = {"_synthetic": True}
_WINDOW = 10 * 60 * 1000
_TEST_CHANNEL = Channel("channel_a", "account_a", ("synthetic_id", "synthetic_caption"))


class FakeReadError(RuntimeError):
    def __init__(self, kind: str) -> None:
        super().__init__("synthetic provider failure")
        self.kind = kind


class FakePostReader:
    def __init__(self) -> None:
        self.posts: list[tuple[str, ChannelPost]] = []
        self.by_id: dict[tuple[str, str], ChannelPost] = {}
        self.fail_list: dict[int, str] = {}
        self.fields_seen: list[tuple[str, tuple[str, ...]]] = []

    def list_recent_posts(
        self,
        account_id: str,
        since_ms: int,
        until_ms: int,
        fields: Sequence[str],
        max_pages: int,
    ) -> list[ChannelPost]:
        self.fields_seen.append((account_id, tuple(fields)))
        channel_id = account_id.replace("account_", "channel_")
        if since_ms in self.fail_list:
            raise FakeReadError(self.fail_list[since_ms])
        return [
            post
            for post_channel, post in self.posts
            if post_channel == channel_id and since_ms <= post.created_at_ms <= until_ms
        ]

    def get_post(self, account_id: str, post_id: str, fields: Sequence[str]) -> ChannelPost:
        channel_id = account_id.replace("account_", "channel_")
        try:
            return self.by_id[(channel_id, post_id)]
        except KeyError:
            raise FakeReadError("NOT_FOUND") from None


def test_reconcile_preserves_statuses_when_provider_is_available() -> None:
    base = 10_000_000
    slots = [
        ScheduledSlot("tracked", base, "Approved synthetic caption"),
        ScheduledSlot("untracked", base + 86_400_000, "Approved synthetic caption"),
        ScheduledSlot("caption-diff", base + 2 * 86_400_000, "Approved synthetic caption"),
        ScheduledSlot("missing", base + 3 * 86_400_000, "Approved synthetic caption"),
        ScheduledSlot("deleted", base + 4 * 86_400_000, "Approved synthetic caption"),
        ScheduledSlot("placeholder", base + 5 * 86_400_000, "Approved synthetic caption"),
        ScheduledSlot("unavailable", base + 6 * 86_400_000, "Approved synthetic caption"),
    ]
    registry = [
        RegistryEntry("channel_a", "tracked", "post-1", "Approved synthetic caption"),
        RegistryEntry("channel_a", "caption-diff", "post-3", "Approved synthetic caption"),
        RegistryEntry("channel_a", "deleted", "post-5", "Approved synthetic caption"),
        RegistryEntry("channel_a", "placeholder", "3. Post ID", "Approved synthetic caption"),
    ]
    reader = FakePostReader()
    reader.posts.extend(
        [
            ("channel_a", ChannelPost("post-1", "Approved synthetic caption", slots[0].scheduled_at_ms + 60_000)),
            ("channel_a", ChannelPost("post-2", "Approved synthetic caption", slots[1].scheduled_at_ms + 60_000)),
        ]
    )
    reader.by_id[("channel_a", "post-3")] = ChannelPost("post-3", "Manual synthetic caption", slots[2].scheduled_at_ms + 60_000)
    reader.fail_list[slots[6].scheduled_at_ms - _WINDOW] = "PERMISSION"

    report = reconcile_channels(slots, [_TEST_CHANNEL], registry, reader)

    assert [row.status for row in report] == [
        ChannelReconcileStatus.TRACKED,
        ChannelReconcileStatus.UNTRACKED,
        ChannelReconcileStatus.CAPTION_DIFF,
        ChannelReconcileStatus.MISSING,
        ChannelReconcileStatus.DELETED,
        ChannelReconcileStatus.PLACEHOLDER,
        ChannelReconcileStatus.UNAVAILABLE,
    ]
    assert all(row.since_ms == slot.scheduled_at_ms - _WINDOW for row, slot in zip(report, slots))
    assert all(row.until_ms == slot.scheduled_at_ms + 3 * 60 * 60 * 1000 for row, slot in zip(report, slots))
    assert reader.fields_seen == [("account_a", ("synthetic_id", "synthetic_caption"))] * 6


def test_graph_error_is_unavailable_not_missing() -> None:
    slot = ScheduledSlot("slot-1", 10_000_000, "Approved synthetic caption")
    reader = FakePostReader()
    reader.fail_list[slot.scheduled_at_ms - _WINDOW] = "PERMISSION"

    report = reconcile_channels([slot], [_TEST_CHANNEL], [], reader)

    assert report[0].status is ChannelReconcileStatus.UNAVAILABLE
    assert report[0].status is not ChannelReconcileStatus.MISSING


def test_alert_deduplication_uses_channel_slot_and_status() -> None:
    slots = [ScheduledSlot("slot-1", 10_000_000, "Approved synthetic caption")]
    reader = FakePostReader()
    first = reconcile_channels(slots, [_TEST_CHANNEL], [], reader)
    second = reconcile_channels(slots, [_TEST_CHANNEL], [], reader)

    alerts = select_new_alerts(first + second, sent_keys={first[0].alert_key})

    assert alerts == []


def test_registry_reader_retries_partial_json_and_never_writes_source(tmp_path: Path) -> None:
    path = tmp_path / "registry.json"
    path.write_text('{"_synthetic": true, "publications":', encoding="utf-8")
    original_mtime = path.stat().st_mtime_ns

    def repair_fixture(_delay: float) -> None:
        path.write_text(json.dumps({**_SYNTHETIC, "publications": []}), encoding="utf-8")

    result = load_registry_with_retries(path, attempts=3, sleep=repair_fixture)

    assert result["_synthetic"] is True
    assert result["publications"] == []
    assert path.stat().st_mtime_ns != original_mtime


def test_registry_reader_is_read_only_when_json_is_valid(tmp_path: Path) -> None:
    path = tmp_path / "registry.json"
    path.write_text(json.dumps({**_SYNTHETIC, "publications": []}), encoding="utf-8")
    original_mtime = path.stat().st_mtime_ns

    result = load_registry_with_retries(path, attempts=3, sleep=lambda _delay: None)

    assert result["_synthetic"] is True
    assert path.stat().st_mtime_ns == original_mtime
