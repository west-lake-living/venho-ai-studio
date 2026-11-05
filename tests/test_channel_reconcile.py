from __future__ import annotations

# _synthetic: true — cần thay bằng fixture thật từ P0-T03/P0-T04.

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from analytics_feedback.channel_reconcile import reconcile_channels


class _FakeClient:
    def __init__(self, posts):
        self.posts = posts
        self.calls = []

    def list_recent_posts(self, account_id, since_ms, until_ms, fields, max_pages):
        self.calls.append((account_id, since_ms, until_ms, tuple(fields), max_pages))
        return self.posts

    def get_object(self, object_id, fields):
        raise AssertionError("known post should be found in the recent-post edge")


class _FakeTelegram:
    def __init__(self):
        self.sent = []

    def send(self, *, chat_id, text):
        self.sent.append({"chat_id": chat_id, "text": text})
        return {"ok": True}


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".json":
        path.write_text(json.dumps(payload), encoding="utf-8")
    else:
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _sources(tmp_path: Path):
    config_root = tmp_path / "config"
    data_root = tmp_path / "data"
    channels = {
        "channels": [
            {"channel_id": "fb_hanoi", "environment": "production", "platform": "facebook", "remote_page_id": "page-hanoi"},
            {"channel_id": "fb_venho", "environment": "production", "platform": "facebook", "remote_page_id": "page-venho"},
            {"channel_id": "ig_venho", "environment": "production", "platform": "instagram", "remote_account_id": "ig-account"},
        ]
    }
    candidates = {
        "api_version": "vTEST",
        "channels": {
            channel_id: {"api_version": "vTEST", "token_env": f"TOKEN_{channel_id}", "collection_edge": "posts", "post_fields": ["id", "message", "created_time"], "max_pages": 2}
            for channel_id in ("fb_hanoi", "fb_venho", "ig_venho")
        },
    }
    cadence = {
        "timezone": "Asia/Ho_Chi_Minh",
        "publish_time": "09:00",
        "slots": [{"day": "wednesday"}],
    }
    registry = {
        "publications": [
            {
                "publication_id": "pub-synthetic",
                "content_package_id": "package-synthetic",
                "slot_id": "slot-2026-11-04-wednesday",
                "platform": "facebook",
                "status": "PUBLISHED",
                "platform_post_id": "post-hanoi-synthetic",
                "content": {"text": "Synthetic lakeside caption"},
            }
        ]
    }
    _write(config_root / "growth_engine" / "channels.yaml", channels)
    _write(config_root / "growth_engine" / "meta_probe_candidates.yaml", candidates)
    _write(config_root / "growth" / "cadence_policy.yaml", cadence)
    registry_path = data_root / "venho_hotel" / "publishing" / "publication_registry.json"
    _write(registry_path, registry)
    return config_root, data_root, registry_path


def test_reconcile_tracks_hanoi_and_finds_untracked_venho_without_touching_legacy_data(tmp_path: Path) -> None:
    config_root, data_root, registry_path = _sources(tmp_path)
    registry_mtime = registry_path.stat().st_mtime_ns
    clients = {
        "fb_hanoi": _FakeClient([{"id": "post-hanoi-synthetic", "message": "Synthetic lakeside caption", "created_time": "2026-11-04T09:15:00+07:00"}]),
        "fb_venho": _FakeClient([{"id": "post-venho-synthetic", "message": "Synthetic lakeside caption", "created_time": "2026-11-04T09:17:00+07:00"}]),
        "ig_venho": _FakeClient([]),
    }

    output = reconcile_channels(
        days=2,
        config_root=config_root,
        data_root=data_root,
        reports_root=tmp_path / "outside-git",
        now=datetime(2026, 11, 5, 12, 0, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh")),
        env={"TOKEN_fb_hanoi": "synthetic", "TOKEN_fb_venho": "synthetic", "TOKEN_ig_venho": "synthetic"},
        client_factory=lambda channel, env: clients[channel["channel_id"]],
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    statuses = {(row["channel_id"], row["status"]) for row in report["results"]}
    assert statuses == {("fb_hanoi", "TRACKED"), ("fb_venho", "UNTRACKED"), ("ig_venho", "MISSING")}
    assert registry_path.stat().st_mtime_ns == registry_mtime
    assert output.is_relative_to(tmp_path / "outside-git")


def test_reconcile_sends_new_alert_once_and_records_dedupe_outside_registry(tmp_path: Path) -> None:
    config_root, data_root, _ = _sources(tmp_path)
    clients = {key: _FakeClient([]) for key in ("fb_hanoi", "fb_venho", "ig_venho")}
    notifier = _FakeTelegram()
    shared = {
        "days": 2,
        "config_root": config_root,
        "data_root": data_root,
        "reports_root": tmp_path / "reports",
        "now": datetime(2026, 11, 5, 12, 0, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh")),
        "env": {"TOKEN_fb_hanoi": "synthetic", "TOKEN_fb_venho": "synthetic", "TOKEN_ig_venho": "synthetic"},
        "client_factory": lambda channel, env: clients[channel["channel_id"]],
        "telegram_notifier": notifier,
        "telegram_chat_id": "synthetic-chat",
        "send_telegram": True,
    }

    reconcile_channels(**shared)
    reconcile_channels(**shared)

    assert len(notifier.sent) == 3
    assert (tmp_path / "reports" / "channel_reconcile" / "alerted.json").exists()
