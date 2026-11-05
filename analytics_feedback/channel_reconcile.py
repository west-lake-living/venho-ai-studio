from __future__ import annotations

import json
import os
import re
import tempfile
import time
import unicodedata
from collections import Counter
from datetime import date, datetime, time as local_time, timedelta
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from zoneinfo import ZoneInfo

import yaml

from shared.meta.graph_client import MetaErrorKind, MetaGraphError, ReadOnlyGraphClient
from shared.notify.telegram import TelegramNotifier


WINDOW_BEFORE_MS = 10 * 60 * 1000
WINDOW_AFTER_MS = 3 * 60 * 60 * 1000
ALERT_STATUSES = {"MISSING", "DELETED", "PLACEHOLDER", "UNAVAILABLE"}
SLOT_DATE = re.compile(r"^slot-(\d{4}-\d{2}-\d{2})-")
PLATFORM_CHANNEL = {"facebook": "fb_hanoi", "instagram": "ig_venho"}


def _read_json_retry(path: Path, attempts: int = 3, retry_delay_seconds: float = 0.05) -> dict[str, Any]:
    for index in range(attempts):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            if index + 1 == attempts:
                raise ValueError("could not read a complete publication registry snapshot") from None
            time.sleep(retry_delay_seconds)
            continue
        if not isinstance(payload, dict) or not isinstance(payload.get("publications"), list):
            raise ValueError("publication registry has an invalid shape")
        return payload
    raise ValueError("could not read a complete publication registry snapshot")


def _write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _caption_prefix(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value).replace("\r\n", "\n")
    return " ".join(normalized.split()).casefold()[:80]


def _parse_timestamp(value: object) -> int | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
    return int(parsed.timestamp() * 1000)


def _post(row: Mapping[str, Any], platform: str) -> dict[str, Any] | None:
    post_id = row.get("id")
    created = _parse_timestamp(row.get("created_time") if platform == "facebook" else row.get("timestamp"))
    if not isinstance(post_id, str) or not post_id or created is None:
        return None
    return {
        "post_id": post_id,
        "caption": str(row.get("message") or row.get("caption") or ""),
        "created_at_ms": created,
        "permalink": row.get("permalink_url") or row.get("permalink"),
    }


def _is_placeholder(post_id: object) -> bool:
    if not isinstance(post_id, str) or not post_id.strip():
        return False
    value = post_id.casefold().strip()
    return value in {"null", "none"} or any(part in value for part in ("post id", "permalink", "required_from_p0", "{{", "}}")) or value.startswith("test_")


def _error_kind(error: Exception) -> str:
    kind = getattr(error, "kind", None)
    return str(getattr(kind, "value", kind) or "").upper()


def _load_sources(
    *, channels_path: Path, candidates_path: Path, cadence_path: Path, registry_path: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any], dict[str, Any], dict[str, Any]]:
    channels_doc = yaml.safe_load(channels_path.read_text(encoding="utf-8")) or {}
    candidates_doc = yaml.safe_load(candidates_path.read_text(encoding="utf-8")) or {}
    cadence_doc = yaml.safe_load(cadence_path.read_text(encoding="utf-8")) or {}
    registry = _read_json_retry(registry_path)
    channels: dict[str, dict[str, Any]] = {}
    for row in channels_doc.get("channels", []):
        if row.get("environment") != "production":
            continue
        channel_id = row.get("channel_id")
        candidate = (candidates_doc.get("channels") or {}).get(channel_id)
        account_id = row.get("remote_page_id") or row.get("remote_account_id")
        if channel_id in {"fb_hanoi", "fb_venho", "ig_venho"} and candidate and account_id:
            channels[channel_id] = {**row, "remote_account_id": str(account_id), "candidate": candidate}
    if set(channels) != {"fb_hanoi", "fb_venho", "ig_venho"}:
        raise ValueError("channels.yaml and Meta probe candidates must define all three production channels")
    if not isinstance(cadence_doc.get("slots"), list):
        raise ValueError("cadence policy has no slots list")
    return channels, candidates_doc, cadence_doc, registry


def _slots_for_window(
    *, registry: Mapping[str, Any], cadence: Mapping[str, Any], days: int, now: datetime,
) -> dict[str, dict[str, Any]]:
    timezone_name = str(cadence.get("timezone") or "Asia/Ho_Chi_Minh")
    zone = ZoneInfo(timezone_name)
    current = now.astimezone(zone)
    publish_time = local_time.fromisoformat(str(cadence.get("publish_time") or "09:00"))
    weekdays = {str(row.get("day", "")).lower() for row in cadence["slots"]}
    slots: dict[str, dict[str, Any]] = {}
    for offset in range(days):
        day = current.date() - timedelta(days=days - offset - 1)
        weekday = day.strftime("%A").lower()
        if weekday in weekdays:
            slot_id = f"slot-{day.isoformat()}-{weekday}"
            scheduled = datetime.combine(day, publish_time, tzinfo=zone)
            slots[slot_id] = {"slot_id": slot_id, "scheduled_at_ms": int(scheduled.timestamp() * 1000)}
    start = current.date() - timedelta(days=days - 1)
    for row in registry.get("publications", []):
        slot_id = row.get("slot_id")
        match = SLOT_DATE.match(str(slot_id or ""))
        if not match:
            continue
        try:
            slot_day = date.fromisoformat(match.group(1))
        except ValueError:
            continue
        if start <= slot_day <= current.date() and slot_id not in slots:
            weekday = slot_day.strftime("%A").lower()
            scheduled = datetime.combine(slot_day, publish_time, tzinfo=zone)
            slots[str(slot_id)] = {"slot_id": str(slot_id), "scheduled_at_ms": int(scheduled.timestamp() * 1000), "weekday": weekday}
    return slots


def _registry_entries(registry: Mapping[str, Any], slots: Mapping[str, Any]) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[str, str]]:
    by_channel_slot: dict[tuple[str, str], dict[str, Any]] = {}
    captions: dict[str, str] = {}
    for row in registry.get("publications", []):
        slot_id = row.get("slot_id")
        platform = row.get("platform")
        if slot_id not in slots or platform not in PLATFORM_CHANNEL or row.get("status") != "PUBLISHED":
            continue
        channel_id = PLATFORM_CHANNEL[platform]
        content = row.get("content") if isinstance(row.get("content"), dict) else {}
        caption = str(content.get("text") or "")
        if caption and slot_id not in captions:
            captions[str(slot_id)] = caption
        by_channel_slot[(channel_id, str(slot_id))] = {
            "post_id": row.get("platform_post_id"),
            "caption": caption,
            "publication_id": row.get("publication_id"),
        }
    return by_channel_slot, captions


def _client_for(channel: Mapping[str, Any], *, env: Mapping[str, str]) -> ReadOnlyGraphClient:
    candidate = channel["candidate"]
    token_env = str(candidate["token_env"])
    token = env.get(token_env, "").strip()
    if not token:
        raise ValueError(f"required environment variable {token_env} is empty")
    return ReadOnlyGraphClient(
        api_version=str(candidate["api_version"]),
        access_token=token,
        collection_edge=str(candidate["collection_edge"]),
    )


def _reconcile_one(
    *, channel: Mapping[str, Any], slot: Mapping[str, Any], entry: Mapping[str, Any] | None,
    expected_caption: str, client: Any,
) -> dict[str, Any]:
    channel_id = str(channel["channel_id"])
    candidate = channel["candidate"]
    platform = str(channel["platform"])
    account_id = str(channel["remote_account_id"])
    fields = list(candidate["post_fields"])
    since_ms = int(slot["scheduled_at_ms"]) - WINDOW_BEFORE_MS
    until_ms = int(slot["scheduled_at_ms"]) + WINDOW_AFTER_MS
    common = {
        "channel_id": channel_id, "remote_account_id": account_id, "slot_id": slot["slot_id"],
        "since_ms": since_ms, "until_ms": until_ms,
    }
    if entry is not None and _is_placeholder(entry.get("post_id")):
        return {**common, "status": "PLACEHOLDER", "post_id": entry.get("post_id")}
    try:
        raw_posts = client.list_recent_posts(account_id, since_ms, until_ms, fields, int(candidate.get("max_pages", 3)))
    except Exception:
        return {**common, "status": "UNAVAILABLE"}
    posts = [post for raw in raw_posts if (post := _post(raw, platform)) is not None and since_ms <= post["created_at_ms"] <= until_ms]
    if entry is not None and entry.get("post_id"):
        known = next((post for post in posts if post["post_id"] == entry["post_id"]), None)
        if known is None:
            try:
                raw = client.get_object(str(entry["post_id"]), fields)
            except Exception as error:
                status = "DELETED" if _error_kind(error) == MetaErrorKind.NOT_FOUND.value else "UNAVAILABLE"
                return {**common, "status": status, "post_id": entry["post_id"]}
            known = _post(raw, platform)
        if known is None:
            return {**common, "status": "UNAVAILABLE", "post_id": entry["post_id"]}
        caption = str(entry.get("caption") or expected_caption)
        status = "TRACKED" if not caption or _caption_prefix(known["caption"]) == _caption_prefix(caption) else "CAPTION_DIFF"
        return {**common, "status": status, "post_id": known["post_id"], "permalink": known["permalink"], "created_at_ms": known["created_at_ms"]}
    matching = next((post for post in posts if expected_caption and _caption_prefix(post["caption"]) == _caption_prefix(expected_caption)), None)
    if matching is not None:
        status = "UNTRACKED"
    elif posts:
        matching = posts[0]
        status = "CAPTION_DIFF"
    else:
        status = "MISSING"
    result = {**common, "status": status}
    if matching:
        result.update(post_id=matching["post_id"], permalink=matching["permalink"], created_at_ms=matching["created_at_ms"])
    return result


def reconcile_channels(
    *, days: int = 7,
    project: str = "venho_hotel",
    config_root: Path = Path("config/projects/venho_hotel"),
    data_root: Path = Path("data/projects"),
    reports_root: Path | None = None,
    now: datetime | None = None,
    env: Mapping[str, str] | None = None,
    client_factory: Callable[[Mapping[str, Any], Mapping[str, str]], Any] = _client_for,
    telegram_notifier: TelegramNotifier | None = None,
    telegram_chat_id: str | None = None,
    send_telegram: bool = False,
) -> Path:
    if not 1 <= days <= 365:
        raise ValueError("days must be between 1 and 365")
    environment = env or os.environ
    root = reports_root or Path(environment.get("GE_GROWTH_REPORTS_DIR", "~/venho/state/growth-reports")).expanduser()
    channels_path = config_root / "growth_engine" / "channels.yaml"
    candidates_path = config_root / "growth_engine" / "meta_probe_candidates.yaml"
    cadence_path = config_root / "growth" / "cadence_policy.yaml"
    registry_path = data_root / project / "publishing" / "publication_registry.json"
    channels, _, cadence, registry = _load_sources(
        channels_path=channels_path, candidates_path=candidates_path,
        cadence_path=cadence_path, registry_path=registry_path,
    )
    zone = ZoneInfo(str(cadence.get("timezone") or "Asia/Ho_Chi_Minh"))
    current = now or datetime.now(zone)
    if current.tzinfo is None:
        current = current.replace(tzinfo=zone)
    slots = _slots_for_window(registry=registry, cadence=cadence, days=days, now=current)
    entries, captions = _registry_entries(registry, slots)
    clients: dict[str, Any] = {}
    results: list[dict[str, Any]] = []
    for slot in sorted(slots.values(), key=lambda item: item["scheduled_at_ms"]):
        for channel_id in ("fb_hanoi", "fb_venho", "ig_venho"):
            channel = channels[channel_id]
            if channel_id not in clients:
                clients[channel_id] = client_factory(channel, environment)
            results.append(_reconcile_one(
                channel=channel, slot=slot, entry=entries.get((channel_id, slot["slot_id"])),
                expected_caption=captions.get(slot["slot_id"], ""), client=clients[channel_id],
            ))
    counts = Counter(row["status"] for row in results)
    report = {
        "schema_version": "growth.channel-reconcile.v1",
        "generated_at": current.isoformat(),
        "days": days,
        "results": results,
        "summary": dict(sorted(counts.items())),
    }
    report_dir = root / "channel_reconcile"
    output = report_dir / f"{current.date().isoformat()}.json"
    _write_json_atomic(output, report)
    if send_telegram and telegram_notifier is not None and telegram_chat_id:
        state_path = report_dir / "alerted.json"
        try:
            sent = set(json.loads(state_path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError, TypeError):
            sent = set()
        new_keys: list[str] = []
        for row in results:
            if row["status"] not in ALERT_STATUSES:
                continue
            alert_key = f"{row['slot_id']}|{row['channel_id']}|{row['status']}"
            if alert_key in sent:
                continue
            message = f"Growth reconcile {row['status']}: {row['slot_id']} · {row['channel_id']}"
            try:
                response = telegram_notifier.send(chat_id=telegram_chat_id, text=message)
            except Exception:
                continue
            if response.get("ok", True):
                new_keys.append(alert_key)
        if new_keys:
            _write_json_atomic(state_path, sorted(sent | set(new_keys)))
    return output
