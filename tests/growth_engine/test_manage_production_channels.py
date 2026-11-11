from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path

from growth_engine.adapters.outbound.persistence.sqlite.connection import connect
from growth_engine.adapters.outbound.persistence.sqlite.migrator import MigrationRunner


_SCRIPT = Path("ops/asus-server/growth-engine/manage-production-channels.py")
_SPEC = importlib.util.spec_from_file_location("manage_production_channels", _SCRIPT)
assert _SPEC and _SPEC.loader
channels = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = channels
_SPEC.loader.exec_module(channels)

MIGRATIONS = Path("growth_engine/adapters/outbound/persistence/sqlite/migrations")


def _db(path: Path) -> None:
    connection = connect(path)
    try:
        MigrationRunner(MIGRATIONS).apply(connection, application_version="pytest")
    finally:
        connection.close()


def _manifest() -> dict:
    values = {
        "fb_hanoi": ("facebook", "1124616474074140", "Ven Hồ Hotel Hanoi", "GE_MAKE_WEBHOOK_URL_PAGE_A"),
        "fb_venho": ("facebook", "803531149684177", "Ven Hồ Hotel", "GE_MAKE_WEBHOOK_URL_PAGE_B"),
        "ig_venho": ("instagram", "17841457936965829", "Ven Hồ Hotel Instagram", "GE_MAKE_WEBHOOK_URL_IG_VENHO"),
    }
    rows = []
    for key, (platform, remote_id, name, route) in values.items():
        row = {
            "channel_id": key, "environment": "production", "platform": platform,
            "display_name": name, "make_route_ref": route, "graph_api_version": "v27.0",
            "make_scenario_id": "5868920", "make_connection_ref": "Production Make connection",
            "owner": "Harry", "verified_on": "2026-11-11", "caption_profile": "default",
            "scopes": ["executions.authorize", "receipts.write", "media.read"],
            "meta_read_token_ref": "GE_META_READ_TOKEN_TEST_ONLY", "enabled": False,
        }
        row["remote_page_id" if platform == "facebook" else "remote_account_id"] = remote_id
        rows.append(row)
    return {"channels": rows}


def _controls(path: Path, mode: str = "DISABLED") -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            """INSERT INTO runtime_controls
               (environment, publish_mode, dispatch_epoch, global_pause, policy_version, updated_at)
               VALUES ('production', ?, 'synthetic-epoch', 1, 'test-policy', 1)""",
            (mode,),
        )
        connection.commit()
    finally:
        connection.close()


def test_provisions_three_disabled_channels_idempotently_with_configs_and_audit(tmp_path: Path) -> None:
    path = tmp_path / "growth_engine.db"
    _db(path)

    first = channels.provision(path, _manifest(), now_ms=100)
    second = channels.provision(path, _manifest(), now_ms=200)

    assert first == "provisioned_or_verified=3 new_rows=6 enabled=0"
    assert second == "provisioned_or_verified=3 new_rows=0 enabled=0"
    connection = sqlite3.connect(path)
    try:
        rows = connection.execute(
            "SELECT channel_key, remote_account_id, enabled FROM channels WHERE environment='production' ORDER BY channel_key"
        ).fetchall()
        configs = connection.execute(
            "SELECT count(*) FROM channel_configs WHERE channel_id LIKE 'production-%'"
        ).fetchone()[0]
        events = connection.execute(
            "SELECT count(*) FROM audit_events WHERE aggregate_type='channel'"
        ).fetchone()[0]
    finally:
        connection.close()
    assert rows == [
        ("fb_hanoi", "1124616474074140", 0),
        ("fb_venho", "803531149684177", 0),
        ("ig_venho", "17841457936965829", 0),
    ]
    assert configs == 3
    assert events == 6


def test_staged_enable_requires_live_manual_pause_and_route_order(tmp_path: Path) -> None:
    path = tmp_path / "growth_engine.db"
    _db(path)
    channels.provision(path, _manifest(), now_ms=100)
    _controls(path, "DISABLED")

    def denied(key: str) -> None:
        try:
            channels.set_enabled(path, key, True, now_ms=200)
        except channels.ChannelSetupError:
            return
        raise AssertionError("unsafe target opening must be refused")

    denied("fb_hanoi")
    connection = sqlite3.connect(path)
    connection.execute("UPDATE runtime_controls SET publish_mode='LIVE_MANUAL' WHERE environment='production'")
    connection.commit()
    connection.close()

    assert channels.set_enabled(path, "fb_hanoi", True, now_ms=300) == "channel=fb_hanoi enabled=1"
    denied("ig_venho")
    assert channels.set_enabled(path, "fb_venho", True, now_ms=400) == "channel=fb_venho enabled=1"
    assert channels.set_enabled(path, "ig_venho", True, now_ms=500) == "channel=ig_venho enabled=1"

    connection = sqlite3.connect(path)
    try:
        states = connection.execute(
            "SELECT channel_key, enabled FROM channels WHERE environment='production' ORDER BY channel_key"
        ).fetchall()
        actions = connection.execute(
            "SELECT action FROM audit_events WHERE aggregate_type='channel' AND action IN ('enable','disable') ORDER BY created_at"
        ).fetchall()
    finally:
        connection.close()
    assert states == [("fb_hanoi", 1), ("fb_venho", 1), ("ig_venho", 1)]
    assert [row[0] for row in actions] == ["enable", "enable", "enable"]


def test_refuses_unverified_ids_or_missing_connection_metadata(tmp_path: Path) -> None:
    path = tmp_path / "growth_engine.db"
    _db(path)
    document = _manifest()
    document["channels"][1]["remote_page_id"] = "wrong-id"
    try:
        channels.provision(path, document, now_ms=100)
    except channels.ChannelSetupError as error:
        assert "IDs" in str(error)
    else:
        raise AssertionError("wrong production Page ID must be rejected")

    document = _manifest()
    document["channels"][2]["make_connection_ref"] = None
    try:
        channels.provision(path, document, now_ms=100)
    except channels.ChannelSetupError:
        pass
    else:
        raise AssertionError("unverified Make connection must be rejected")
