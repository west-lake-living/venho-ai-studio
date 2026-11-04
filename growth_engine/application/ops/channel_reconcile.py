from __future__ import annotations

import json
import time
import unicodedata
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Optional, Protocol, Sequence


WINDOW_BEFORE_MS = 10 * 60 * 1000
WINDOW_AFTER_MS = 3 * 60 * 60 * 1000
MAX_PAGES = 3
_ALERT_STATUSES = {
    "MISSING",
    "DELETED",
    "PLACEHOLDER",
    "UNAVAILABLE",
}


class ChannelReconcileStatus(str, Enum):
    TRACKED = "TRACKED"
    UNTRACKED = "UNTRACKED"
    CAPTION_DIFF = "CAPTION_DIFF"
    MISSING = "MISSING"
    DELETED = "DELETED"
    PLACEHOLDER = "PLACEHOLDER"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class Channel:
    channel_id: str
    remote_account_id: str
    fields: tuple[str, ...]


@dataclass(frozen=True)
class ScheduledSlot:
    slot_id: str
    scheduled_at_ms: int
    caption: str


@dataclass(frozen=True)
class RegistryEntry:
    channel_id: str
    slot_id: str
    post_id: Optional[str]
    caption: str


@dataclass(frozen=True)
class ChannelPost:
    post_id: str
    caption: str
    created_at_ms: int
    permalink: Optional[str] = None


@dataclass(frozen=True)
class ChannelReconcileResult:
    channel_id: str
    remote_account_id: str
    slot_id: str
    status: ChannelReconcileStatus
    since_ms: int
    until_ms: int
    post_id: Optional[str] = None
    permalink: Optional[str] = None

    @property
    def alert_key(self) -> str:
        return f"{self.slot_id}|{self.channel_id}|{self.status.value}"


class ChannelPostReader(Protocol):
    def list_recent_posts(
        self,
        account_id: str,
        since_ms: int,
        until_ms: int,
        fields: Sequence[str],
        max_pages: int,
    ) -> Sequence[ChannelPost]:
        """Return normalized posts; provider field names come from channel config."""

    def get_post(self, account_id: str, post_id: str, fields: Sequence[str]) -> ChannelPost:
        """Read a known post; NOT_FOUND must be distinct from access failures."""


class RegistryReadError(RuntimeError):
    pass


def load_registry_with_retries(
    path: Path,
    *,
    attempts: int = 3,
    retry_delay_seconds: float = 0.05,
    sleep: Callable[[float], None] = time.sleep,
) -> dict:
    """Read a registry snapshot, retrying partial JSON without changing the file."""
    if attempts < 1:
        raise ValueError("attempts must be at least one")
    for attempt in range(attempts):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            if attempt + 1 == attempts:
                raise RegistryReadError("could not read a complete registry snapshot") from None
            sleep(retry_delay_seconds)
            continue
        if not isinstance(value, dict) or not isinstance(value.get("publications"), list):
            raise RegistryReadError("registry snapshot has an invalid shape")
        return value
    raise RegistryReadError("could not read a complete registry snapshot")


def reconcile_channels(
    slots: Sequence[ScheduledSlot],
    channels: Sequence[Channel],
    registry_entries: Sequence[RegistryEntry],
    reader: ChannelPostReader,
    *,
    max_pages: int = MAX_PAGES,
) -> list[ChannelReconcileResult]:
    if max_pages < 1:
        raise ValueError("max_pages must be at least one")
    registry_by_key: dict[tuple[str, str], RegistryEntry] = {}
    for entry in registry_entries:
        key = (entry.slot_id, entry.channel_id)
        if key in registry_by_key:
            raise ValueError(f"duplicate registry entry for {entry.slot_id}/{entry.channel_id}")
        registry_by_key[key] = entry

    results: list[ChannelReconcileResult] = []
    for slot in slots:
        since_ms = slot.scheduled_at_ms - WINDOW_BEFORE_MS
        until_ms = slot.scheduled_at_ms + WINDOW_AFTER_MS
        for channel in channels:
            entry = registry_by_key.get((slot.slot_id, channel.channel_id))
            base = {
                "channel_id": channel.channel_id,
                "remote_account_id": channel.remote_account_id,
                "slot_id": slot.slot_id,
                "since_ms": since_ms,
                "until_ms": until_ms,
            }
            if entry is not None and _is_placeholder_post_id(entry.post_id):
                results.append(
                    ChannelReconcileResult(**base, status=ChannelReconcileStatus.PLACEHOLDER, post_id=entry.post_id)
                )
                continue
            try:
                posts = list(
                    reader.list_recent_posts(
                        channel.remote_account_id,
                        since_ms,
                        until_ms,
                        channel.fields,
                        max_pages,
                    )
                )
            except Exception:
                results.append(
                    ChannelReconcileResult(**base, status=ChannelReconcileStatus.UNAVAILABLE)
                )
                continue
            posts = [post for post in posts if since_ms <= post.created_at_ms <= until_ms]
            if entry is not None and entry.post_id:
                known = next((post for post in posts if post.post_id == entry.post_id), None)
                if known is not None:
                    status = _compare_caption(known.caption, entry.caption or slot.caption)
                    results.append(ChannelReconcileResult(**base, status=status, post_id=known.post_id, permalink=known.permalink))
                    continue
                try:
                    known = reader.get_post(channel.remote_account_id, entry.post_id, channel.fields)
                except Exception as exc:
                    status = (
                        ChannelReconcileStatus.DELETED
                        if _error_kind(exc) == "NOT_FOUND"
                        else ChannelReconcileStatus.UNAVAILABLE
                    )
                    results.append(ChannelReconcileResult(**base, status=status, post_id=entry.post_id))
                    continue
                status = _compare_caption(known.caption, entry.caption or slot.caption)
                results.append(ChannelReconcileResult(**base, status=status, post_id=known.post_id, permalink=known.permalink))
                continue

            expected_caption = entry.caption if entry is not None and entry.caption else slot.caption
            matching = next(
                (post for post in posts if _caption_prefix(post.caption) == _caption_prefix(expected_caption)),
                None,
            )
            if matching is not None:
                status = ChannelReconcileStatus.UNTRACKED
            elif posts:
                matching = posts[0]
                status = ChannelReconcileStatus.CAPTION_DIFF
            else:
                status = ChannelReconcileStatus.MISSING
            results.append(
                ChannelReconcileResult(
                    **base,
                    status=status,
                    post_id=matching.post_id if matching else None,
                    permalink=matching.permalink if matching else None,
                )
            )
    return results


def select_new_alerts(
    results: Sequence[ChannelReconcileResult],
    *,
    sent_keys: set[str],
) -> list[ChannelReconcileResult]:
    selected: list[ChannelReconcileResult] = []
    seen = set(sent_keys)
    for result in results:
        if result.status.value not in _ALERT_STATUSES or result.alert_key in seen:
            continue
        selected.append(result)
        seen.add(result.alert_key)
    return selected


def _caption_prefix(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value).replace("\r\n", "\n")
    return " ".join(normalized.split()).casefold()[:80]


def _compare_caption(actual: str, expected: str) -> ChannelReconcileStatus:
    if _caption_prefix(actual) == _caption_prefix(expected):
        return ChannelReconcileStatus.TRACKED
    return ChannelReconcileStatus.CAPTION_DIFF


def _is_placeholder_post_id(value: Optional[str]) -> bool:
    if value is None or not value.strip():
        return False
    lowered = value.casefold().strip()
    return (
        lowered in {"null", "none"}
        or "post id" in lowered
        or "permalink" in lowered
        or "required_from_p0" in lowered
        or "{{" in value
        or "}}" in value
        or lowered.startswith("test_")
    )


def _error_kind(error: Exception) -> str:
    kind = getattr(error, "kind", "")
    return str(getattr(kind, "value", kind)).upper()
