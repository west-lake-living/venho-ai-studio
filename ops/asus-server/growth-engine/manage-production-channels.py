#!/usr/bin/env python3
"""Provision verified production channels disabled, or audit one staged enable/disable."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Mapping

import yaml


EXPECTED = {
    "fb_hanoi": ("facebook", "1124616474074140"),
    "fb_venho": ("facebook", "803531149684177"),
    "ig_venho": ("instagram", "17841457936965829"),
}
MANIFEST = Path("config/projects/venho_hotel/growth_engine/channels.yaml")


class ChannelSetupError(ValueError):
    pass


def _canonical(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _append_audit(
    connection: sqlite3.Connection,
    *,
    action: str,
    aggregate_id: str,
    after: Mapping[str, Any],
    now_ms: int,
    before: Mapping[str, Any] | None = None,
) -> None:
    connection.execute(
        """INSERT INTO audit_events
           (id, aggregate_type, aggregate_id, actor, action, before_hash, after_hash,
            details_json, correlation_id, created_at)
           VALUES (?, 'channel', ?, 'production-cutover-operator', ?, ?, ?, ?, ?, ?)""",
        (
            str(uuid.uuid4()), aggregate_id, action, None if before is None else _hash(before), _hash(after), _canonical(dict(after)),
            str(uuid.uuid4()), now_ms,
        ),
    )


def _validate_rows(document: Any) -> list[dict[str, Any]]:
    if not isinstance(document, dict) or not isinstance(document.get("channels"), list):
        raise ChannelSetupError("channels manifest is invalid")
    rows = [row for row in document["channels"] if isinstance(row, dict) and row.get("environment") == "production"]
    by_key = {row.get("channel_id"): row for row in rows}
    if set(by_key) != set(EXPECTED) or len(rows) != len(EXPECTED):
        raise ChannelSetupError("production manifest must contain the three fixed channels")
    normalized: list[dict[str, Any]] = []
    for key, (platform, remote_id) in EXPECTED.items():
        row = by_key[key]
        actual_id = row.get("remote_page_id") if platform == "facebook" else row.get("remote_account_id")
        if actual_id != remote_id or row.get("platform") != platform:
            raise ChannelSetupError("production destination does not match the reviewed Page/account IDs")
        for field in ("display_name", "make_route_ref", "graph_api_version", "make_scenario_id", "make_connection_ref", "owner", "verified_on", "caption_profile"):
            value = row.get(field)
            if not isinstance(value, str) or not value.strip() or "REQUIRED_FROM_P0" in value:
                raise ChannelSetupError(f"production manifest field is not verified: {key}.{field}")
        if not row["make_route_ref"].startswith("GE_MAKE_WEBHOOK_URL_") or not row["graph_api_version"].startswith("v"):
            raise ChannelSetupError(f"production route reference or Graph version is invalid: {key}")
        token_ref = row.get("meta_read_token_ref")
        if not isinstance(token_ref, str) or not token_ref.startswith("GE_META_READ_TOKEN_"):
            raise ChannelSetupError(f"production Meta token reference is missing: {key}")
        if not isinstance(row.get("scopes"), list) or not row["scopes"]:
            raise ChannelSetupError(f"production scopes are missing: {key}")
        if row.get("enabled") is not False:
            raise ChannelSetupError(f"manifest must keep {key} disabled during provisioning")
        normalized.append({
            "key": key,
            "platform": platform,
            "remote_id": remote_id,
            "name": str(row["display_name"]),
            "route_ref": str(row["make_route_ref"]),
            "graph_api_version": str(row["graph_api_version"]),
            "caption_profile": str(row["caption_profile"]),
            "scopes": [str(scope) for scope in row["scopes"]],
            "meta_read_token_ref": str(row.get("meta_read_token_ref", "")),
        })
    return normalized


def provision(db_path: str | Path, manifest_document: Any, *, now_ms: int | None = None) -> str:
    rows = _validate_rows(manifest_document)
    timestamp = time.time_ns() // 1_000_000 if now_ms is None else now_ms
    connection = sqlite3.connect(Path(db_path), timeout=30, isolation_level=None)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("BEGIN IMMEDIATE")
        schema = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
        if schema is None or not isinstance(schema[0], int) or schema[0] < 9:
            raise ChannelSetupError("production schema is not at the reviewed migration level")
        created = 0
        for row in rows:
            channel_id = f"production-{row['key']}"
            config_id = f"production-{row['key']}-config-v1"
            existing = connection.execute(
                "SELECT id, project_id, platform, remote_account_id, name, enabled FROM channels WHERE environment='production' AND channel_key=?",
                (row["key"],),
            ).fetchone()
            if existing is None:
                connection.execute(
                    """INSERT INTO channels
                       (id, project_id, environment, channel_key, platform, remote_account_id, name, enabled, paused, created_at)
                       VALUES (?, 'venho_hotel', 'production', ?, ?, ?, ?, 0, 0, ?)""",
                    (channel_id, row["key"], row["platform"], row["remote_id"], row["name"], timestamp),
                )
                _append_audit(connection, action="provision_disabled", aggregate_id=channel_id,
                              after={"channel_key": row["key"], "remote_id": row["remote_id"], "enabled": False}, now_ms=timestamp)
                created += 1
            elif (
                existing["id"] != channel_id or existing["project_id"] != "venho_hotel"
                or existing["platform"] != row["platform"] or existing["remote_account_id"] != row["remote_id"]
                or existing["name"] != row["name"]
            ):
                raise ChannelSetupError(f"existing production channel identity differs: {row['key']}")
            elif bool(existing["enabled"]):
                raise ChannelSetupError(f"provision is bootstrap-only; channel is already enabled: {row['key']}")

            capability = {"scopes": row["scopes"], "meta_read_token_ref": row["meta_read_token_ref"]}
            config_hash = _hash({
                "channel_id": channel_id, "version": 1, "make_route_ref": row["route_ref"],
                "graph_api_version": row["graph_api_version"], "capability": capability,
                "caption_profile": row["caption_profile"],
            })
            config = connection.execute(
                "SELECT id, version, make_route_ref, graph_api_version, capability_json, caption_profile, config_hash FROM channel_configs WHERE channel_id=? ORDER BY version DESC",
                (channel_id,),
            ).fetchall()
            if not config:
                if existing is not None and bool(existing["enabled"]):
                    raise ChannelSetupError(f"refusing to provision a config for an enabled channel: {row['key']}")
                connection.execute(
                    """INSERT INTO channel_configs
                       (id, channel_id, version, make_route_ref, graph_api_version, capability_json, caption_profile, config_hash, created_at)
                       VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?)""",
                    (config_id, channel_id, row["route_ref"], row["graph_api_version"], _canonical(capability),
                     row["caption_profile"], config_hash, timestamp),
                )
                _append_audit(connection, action="provision_channel_config", aggregate_id=channel_id,
                              after={"channel_key": row["key"], "config_id": config_id, "config_hash": config_hash}, now_ms=timestamp)
                created += 1
            else:
                latest = config[0]
                if (
                    latest["id"] != config_id or latest["version"] != 1
                    or latest["make_route_ref"] != row["route_ref"]
                    or latest["graph_api_version"] != row["graph_api_version"]
                    or latest["capability_json"] != _canonical(capability)
                    or latest["caption_profile"] != row["caption_profile"]
                    or latest["config_hash"] != config_hash
                ):
                    raise ChannelSetupError(f"existing production channel config differs: {row['key']}")
        connection.execute("COMMIT")
        return f"provisioned_or_verified={len(rows)} new_rows={created} enabled=0"
    except Exception:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()


def set_enabled(db_path: str | Path, channel_key: str, enabled: bool, *, now_ms: int | None = None) -> str:
    if channel_key not in EXPECTED or type(enabled) is not bool:
        raise ChannelSetupError("unknown production channel or invalid state")
    timestamp = time.time_ns() // 1_000_000 if now_ms is None else now_ms
    connection = sqlite3.connect(Path(db_path), timeout=30, isolation_level=None)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("BEGIN IMMEDIATE")
        controls = connection.execute(
            "SELECT publish_mode, global_pause FROM runtime_controls WHERE environment='production'"
        ).fetchone()
        if controls is None or controls["global_pause"] != 1:
            raise ChannelSetupError("global pause must be active before a target toggle")
        channel = connection.execute(
            """SELECT id, remote_account_id, enabled, paused,
                      (SELECT count(*) FROM channel_configs cc WHERE cc.channel_id=channels.id) AS config_count
               FROM channels WHERE environment='production' AND channel_key=?""",
            (channel_key,),
        ).fetchone()
        _, expected_id = EXPECTED[channel_key]
        if channel is None or channel["remote_account_id"] != expected_id:
            raise ChannelSetupError("production channel ID does not match the approved target")
        if enabled and (channel["config_count"] < 1 or channel["paused"]):
            raise ChannelSetupError("production channel lacks a config or is paused")
        if bool(channel["enabled"]) == enabled:
            connection.execute("COMMIT")
            return f"channel={channel_key} already_enabled={int(enabled)}"
        if enabled:
            required_predecessors = {"fb_hanoi": (), "fb_venho": ("fb_hanoi",), "ig_venho": ("fb_hanoi", "fb_venho")}[channel_key]
            required_disabled = {"fb_hanoi": ("fb_venho", "ig_venho"), "fb_venho": ("ig_venho",), "ig_venho": ()}[channel_key]
            states = {
                str(row["channel_key"]): bool(row["enabled"])
                for row in connection.execute(
                    "SELECT channel_key, enabled FROM channels WHERE environment='production'"
                )
            }
            if set(states) != set(EXPECTED):
                raise ChannelSetupError("all three production channels must be provisioned before any enable")
            if any(not states.get(key, False) for key in required_predecessors) or any(states.get(key, False) for key in required_disabled):
                raise ChannelSetupError("production targets must open in order fb_hanoi, fb_venho, ig_venho")
            if controls["publish_mode"] != "LIVE_MANUAL":
                raise ChannelSetupError("set runtime mode LIVE_MANUAL while global pause remains active before enabling a target")
        before_state = {"channel_key": channel_key, "remote_id": expected_id, "enabled": bool(channel["enabled"])}
        next_state = {"channel_key": channel_key, "remote_id": expected_id, "enabled": enabled}
        connection.execute("UPDATE channels SET enabled=? WHERE id=?", (int(enabled), channel["id"]))
        _append_audit(connection, action="enable" if enabled else "disable", aggregate_id=channel["id"], after=next_state, now_ms=timestamp, before=before_state)
        connection.execute("COMMIT")
        return f"channel={channel_key} enabled={int(enabled)}"
    except Exception:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()


def _production_db_path() -> Path:
    if os.environ.get("GE_ENV", "").strip() != "production":
        raise ChannelSetupError("GE_ENV must be production")
    raw = os.environ.get("GE_DB_PATH", "").strip()
    if not raw:
        raise ChannelSetupError("GE_DB_PATH is missing")
    path = Path(raw).expanduser().resolve(strict=True)
    path.relative_to((Path.home() / "venho/state/growth-engine").resolve())
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    provision_parser = sub.add_parser("provision")
    provision_parser.add_argument("--manifest", type=Path, default=MANIFEST)
    state_parser = sub.add_parser("set-enabled")
    state_parser.add_argument("--channel", choices=tuple(EXPECTED), required=True)
    group = state_parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--enable", action="store_true")
    group.add_argument("--disable", action="store_true")
    args = parser.parse_args(argv)
    try:
        db_path = _production_db_path()
        if args.command == "provision":
            document = yaml.safe_load(args.manifest.read_text(encoding="utf-8"))
            result = provision(db_path, document)
        else:
            result = set_enabled(db_path, args.channel, args.enable)
    except (OSError, UnicodeError, sqlite3.Error, ValueError, yaml.YAMLError):
        print("FAIL: production channel operation stopped; verify manifest, IDs, state and schema", file=sys.stderr)
        return 1
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
