from __future__ import annotations

import base64
import hashlib
import json
import re
from collections.abc import Callable
from typing import Any

from growth_engine.application.queries.incident_views import IncidentViewsQuery
from growth_engine.application.queries.slot_views import SlotViewsQuery


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class SqliteDashboardReads:
    """Read-only Dashboard projections over the shared SQLite UoW."""

    def __init__(
        self,
        uow_factory: Callable[[], Any],
        *,
        environment: str,
        now_ms: Callable[[], int],
        media_store: Any,
    ) -> None:
        self._uow_factory = uow_factory
        self._environment = environment
        self._now_ms = now_ms
        self._media_store = media_store

    def channels(self) -> dict[str, object]:
        with self._uow_factory().read_only() as tx:
            rows = tx.connection.execute(
                """SELECT c.id, c.channel_key, c.platform, c.remote_account_id, c.name,
                          c.enabled, c.paused, COUNT(cc.id) AS config_count
                   FROM channels c LEFT JOIN channel_configs cc ON cc.channel_id=c.id
                   WHERE c.environment=? GROUP BY c.id
                   ORDER BY c.channel_key""",
                (self._environment,),
            ).fetchall()
        return {
            "items": [
                {
                    "channel_id": row["id"],
                    "channel_key": row["channel_key"],
                    "platform": row["platform"],
                    "remote_account_id": row["remote_account_id"],
                    "name": row["name"],
                    "enabled": bool(row["enabled"]),
                    "paused": bool(row["paused"]),
                    "connection_status": "CONFIGURED" if row["config_count"] else "MISSING_CONFIG",
                }
                for row in rows
            ],
            "as_of_ms": self._now_ms(),
        }

    def load_slot_views(self, query: SlotViewsQuery) -> dict[str, object]:
        with self._uow_factory().read_only() as tx:
            rows = tx.connection.execute(
                """SELECT s.id AS slot_id, s.local_date, s.local_time, s.timezone, s.lane,
                          s.scheduled_at, s.deadline_at, s.cancelled_at, s.row_version,
                          st.id AS target_id, st.required, c.id AS channel_id, c.channel_key,
                          c.platform, c.name AS page_name, c.enabled, c.paused,
                          d.id AS delivery_id, d.state AS delivery_state, d.row_version AS delivery_row_version,
                          d.blocked_reason, d.platform_post_id, d.permalink, p.topic_key, p.pillar,
                          r.id AS revision_id, r.payload_hash, r.caption, v.sha256 AS image_sha256
                   FROM slots s JOIN slot_targets st ON st.slot_id=s.id
                   JOIN channels c ON c.id=st.channel_id
                   LEFT JOIN deliveries d ON d.target_id=st.id AND d.active=1
                   LEFT JOIN content_packages p ON p.id=d.package_id
                   LEFT JOIN delivery_revisions r ON r.id=d.current_revision_id AND r.delivery_id=d.id
                   LEFT JOIN media_variants v ON v.id=r.variant_id
                   WHERE c.environment=? AND s.local_date BETWEEN ? AND ?
                   ORDER BY s.local_date, s.local_time, s.id, c.channel_key""",
                (self._environment, query.from_date, query.to_date),
            ).fetchall()
        slots: dict[str, dict[str, object]] = {}
        for row in rows:
            slot = slots.get(row["slot_id"])
            if slot is None:
                slot = {
                    "slot_id": row["slot_id"],
                    "local_date": row["local_date"],
                    "local_time": row["local_time"],
                    "timezone": row["timezone"],
                    "scheduled_at_ms": int(row["scheduled_at"]),
                    "deadline_at_ms": int(row["deadline_at"]),
                    "row_version": int(row["row_version"]),
                    "etag": f'"slot:{row["slot_id"]}:{row["row_version"]}"',
                    "lane": row["lane"],
                    "cancelled": row["cancelled_at"] is not None,
                    "targets": [],
                    "attention_flags": [],
                }
                slots[row["slot_id"]] = slot
            target = {
                "target_id": row["target_id"],
                "channel_id": row["channel_id"],
                "channel_key": row["channel_key"],
                "platform": row["platform"],
                "page_name": row["page_name"],
                "required": bool(row["required"]),
                "channel_enabled": bool(row["enabled"]),
                "paused": bool(row["paused"]),
                "delivery_id": row["delivery_id"],
                "delivery_state": row["delivery_state"],
                "delivery_row_version": row["delivery_row_version"],
                "revision_id": row["revision_id"],
                "payload_hash": row["payload_hash"],
                "caption": row["caption"],
                "topic_key": row["topic_key"],
                "pillar": row["pillar"],
                "image_sha256": row["image_sha256"],
                "blocked_reason": row["blocked_reason"],
                "platform_post_id": row["platform_post_id"],
                "permalink": row["permalink"],
            }
            slot["targets"].append(target)
            flags = slot["attention_flags"]
            assert isinstance(flags, list)
            if row["delivery_id"] is None:
                flags.append(f"MISSING_DELIVERY:{row['channel_key']}")
            elif row["delivery_state"] in {"IN_REVIEW", "BLOCKED", "UNKNOWN", "FAILED_FINAL"}:
                flags.append(f"{row['delivery_state']}:{row['channel_key']}")
            if not row["enabled"] or row["paused"]:
                flags.append(f"CHANNEL_UNAVAILABLE:{row['channel_key']}")
        return {
            "from": query.from_date,
            "to": query.to_date,
            "items": list(slots.values()),
            "as_of_ms": self._now_ms(),
        }

    def delivery_version(self, delivery_id: str) -> int | None:
        with self._uow_factory().read_only() as tx:
            row = tx.connection.execute(
                "SELECT row_version FROM deliveries WHERE id=?", (delivery_id,)
            ).fetchone()
        return None if row is None else int(row["row_version"])

    def slot_context(self, slot_id: str) -> dict[str, object] | None:
        with self._uow_factory().read_only() as tx:
            row = tx.connection.execute(
                "SELECT id, local_date, local_time, timezone, row_version FROM slots WHERE id=?",
                (slot_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "slot_id": row["id"],
            "local_date": row["local_date"],
            "local_time": row["local_time"],
            "timezone": row["timezone"],
            "row_version": int(row["row_version"]),
        }

    def deliveries(
        self,
        *,
        state: str | None,
        channel_id: str | None,
        cursor: str | None,
        limit: int,
    ) -> dict[str, object]:
        if type(limit) is not int or not 1 <= limit <= 50:
            raise ValueError("limit must be between 1 and 50")
        cursor_values = _decode_cursor(cursor)
        predicates = ["c.environment=?", "d.active=1"]
        parameters: list[object] = [self._environment]
        if state:
            predicates.append("d.state=?")
            parameters.append(state.upper())
        if channel_id:
            predicates.append("d.channel_id=?")
            parameters.append(channel_id)
        if cursor_values is not None:
            predicates.append("(s.scheduled_at < ? OR (s.scheduled_at=? AND d.id < ?))")
            parameters.extend((cursor_values[0], cursor_values[0], cursor_values[1]))
        parameters.append(limit + 1)
        with self._uow_factory().read_only() as tx:
            rows = tx.connection.execute(
                f"""SELECT d.id AS delivery_id, d.state, d.row_version, d.blocked_reason,
                           d.platform_post_id, d.permalink, d.created_at, d.updated_at,
                           c.id AS channel_id, c.channel_key, c.platform, c.name AS page_name,
                           s.id AS slot_id, s.local_date, s.local_time, s.timezone,
                           s.scheduled_at, s.deadline_at, p.topic_key, p.pillar,
                           r.id AS revision_id, r.payload_hash, r.caption, v.sha256 AS image_sha256
                    FROM deliveries d JOIN channels c ON c.id=d.channel_id
                    JOIN slot_targets st ON st.id=d.target_id AND st.channel_id=d.channel_id
                    JOIN slots s ON s.id=st.slot_id JOIN content_packages p ON p.id=d.package_id
                    LEFT JOIN delivery_revisions r ON r.id=d.current_revision_id AND r.delivery_id=d.id
                    LEFT JOIN media_variants v ON v.id=r.variant_id
                    WHERE {' AND '.join(predicates)}
                    ORDER BY s.scheduled_at DESC, d.id DESC LIMIT ?""",
                tuple(parameters),
            ).fetchall()
        has_more = len(rows) > limit
        page = rows[:limit]
        items = [
            {
                "delivery_id": row["delivery_id"],
                "state": row["state"],
                "row_version": int(row["row_version"]),
                "etag": f'"delivery:{row["delivery_id"]}:{row["row_version"]}"',
                "blocked_reason": row["blocked_reason"],
                "channel_id": row["channel_id"],
                "channel_key": row["channel_key"],
                "platform": row["platform"],
                "page_name": row["page_name"],
                "slot_id": row["slot_id"],
                "local_date": row["local_date"],
                "local_time": row["local_time"],
                "timezone": row["timezone"],
                "scheduled_at_ms": int(row["scheduled_at"]),
                "deadline_at_ms": int(row["deadline_at"]),
                "topic_key": row["topic_key"],
                "pillar": row["pillar"],
                "revision_id": row["revision_id"],
                "payload_hash": row["payload_hash"],
                "caption": row["caption"],
                "image_sha256": row["image_sha256"],
                "platform_post_id": row["platform_post_id"],
                "permalink": row["permalink"],
                "created_at_ms": int(row["created_at"]),
                "updated_at_ms": int(row["updated_at"]),
            }
            for row in page
        ]
        next_cursor = None
        if has_more and page:
            last = page[-1]
            next_cursor = _encode_cursor(int(last["scheduled_at"]), str(last["delivery_id"]))
        return {"items": items, "next_cursor": next_cursor, "as_of_ms": self._now_ms()}

    def load_incident_views(self, query: IncidentViewsQuery) -> dict[str, object]:
        if not 1 <= query.limit <= 50:
            raise ValueError("limit must be between 1 and 50")
        state = query.state.upper()
        if state not in {"OPEN", "RESOLVED", "ALL"}:
            raise ValueError("state must be OPEN, RESOLVED, or ALL")
        cursor_values = _decode_incident_cursor(query.cursor)
        predicates: list[str] = []
        parameters: list[object] = []
        if state != "ALL":
            predicates.append("i.state=?")
            parameters.append(state)
        if cursor_values is not None:
            predicates.append("(i.last_seen_at < ? OR (i.last_seen_at=? AND i.id < ?))")
            parameters.extend((cursor_values[0], cursor_values[0], cursor_values[1]))
        parameters.append(query.limit + 1)
        where = " WHERE " + " AND ".join(predicates) if predicates else ""
        with self._uow_factory().read_only() as tx:
            rows = tx.connection.execute(
                f"""SELECT i.id, i.type, i.severity, i.state, i.first_seen_at, i.last_seen_at,
                           i.occurrence_count, i.resolved_at, i.resolved_by, i.details_json
                    FROM incidents i{where}
                    ORDER BY i.last_seen_at DESC, i.id DESC LIMIT ?""",
                tuple(parameters),
            ).fetchall()
        has_more = len(rows) > query.limit
        page = rows[:query.limit]
        items: list[dict[str, object]] = []
        for row in page:
            details = json.loads(row["details_json"])
            items.append({
                "incident_id": row["id"],
                "type": row["type"],
                "severity": row["severity"],
                "state": row["state"],
                "first_seen_at_ms": int(row["first_seen_at"]),
                "last_seen_at_ms": int(row["last_seen_at"]),
                "occurrence_count": int(row["occurrence_count"]),
                "resolved_at_ms": row["resolved_at"],
                "resolved_by": row["resolved_by"],
                "channel_id": details.get("channel_id"),
                "ref": details.get("ref"),
                "resolution_reason": details.get("resolution_reason"),
            })
        next_cursor = None
        if has_more and page:
            last = page[-1]
            next_cursor = _encode_incident_cursor(int(last["last_seen_at"]), str(last["id"]))
        return {"state": state, "items": items, "next_cursor": next_cursor, "as_of_ms": self._now_ms()}

    def candidates(self, *, state: str, cursor: str | None, limit: int) -> dict[str, object]:
        if not 1 <= limit <= 50:
            raise ValueError("limit must be between 1 and 50")
        state = state.upper()
        cursor_values = _decode_candidate_cursor(cursor)
        predicates = ["state=?"]
        parameters: list[object] = [state]
        if cursor_values is not None:
            predicates.append("(created_at < ? OR (created_at=? AND id < ?))")
            parameters.extend((cursor_values[0], cursor_values[0], cursor_values[1]))
        parameters.append(limit + 1)
        with self._uow_factory().read_only() as tx:
            rows = tx.connection.execute(
                f"""SELECT id, project_id, source, external_key, source_revision, event_key,
                           topic_key, event_start_at, event_end_at, expires_at, payload_json,
                           source_hash, state, created_at
                    FROM research_candidates WHERE {' AND '.join(predicates)}
                    ORDER BY created_at DESC, id DESC LIMIT ?""",
                tuple(parameters),
            ).fetchall()
        has_more = len(rows) > limit
        page = rows[:limit]
        items = [
            {
                "candidate_id": row["id"],
                "project_id": row["project_id"],
                "source": row["source"],
                "external_key": row["external_key"],
                "source_revision": row["source_revision"],
                "event_key": row["event_key"],
                "topic_key": row["topic_key"],
                "event_start_at_ms": row["event_start_at"],
                "event_end_at_ms": row["event_end_at"],
                "expires_at_ms": int(row["expires_at"]),
                "payload": json.loads(row["payload_json"]),
                "source_hash": row["source_hash"],
                "state": row["state"],
                "created_at_ms": int(row["created_at"]),
            }
            for row in page
        ]
        next_cursor = None
        if has_more and page:
            last = page[-1]
            next_cursor = _encode_candidate_cursor(int(last["created_at"]), str(last["id"]))
        return {"state": state, "items": items, "next_cursor": next_cursor, "as_of_ms": self._now_ms()}

    def job(self, job_id: str) -> dict[str, object] | None:
        with self._uow_factory().read_only() as tx:
            row = tx.connection.execute(
                """SELECT id, kind, lane, state, attempts, max_attempts, run_at,
                          last_error, created_at, updated_at FROM jobs WHERE id=?""",
                (job_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "job_id": row["id"],
            "kind": row["kind"],
            "lane": row["lane"],
            "state": row["state"],
            "attempts": int(row["attempts"]),
            "max_attempts": int(row["max_attempts"]),
            "run_at_ms": int(row["run_at"]),
            "last_error": row["last_error"],
            "created_at_ms": int(row["created_at"]),
            "updated_at_ms": int(row["updated_at"]),
        }

    def controls(self) -> dict[str, object] | None:
        with self._uow_factory().read_only() as tx:
            controls = tx.controls.get_with_version(self._environment)
            channels = tx.connection.execute(
                """SELECT id, channel_key, name, enabled, paused FROM channels
                   WHERE environment=? ORDER BY channel_key""",
                (self._environment,),
            ).fetchall()
        if controls is None:
            return None
        value, row_version = controls
        return {
            "environment": self._environment,
            "mode": value.mode.value,
            "dispatch_epoch": value.dispatch_epoch,
            "global_pause": value.global_pause,
            "row_version": row_version,
            "channels": [
                {
                    "channel_id": row["id"],
                    "channel_key": row["channel_key"],
                    "name": row["name"],
                    "enabled": bool(row["enabled"]),
                    "paused": bool(row["paused"]),
                }
                for row in channels
            ],
            "as_of_ms": self._now_ms(),
        }

    def preview(self, sha256: str) -> tuple[bytes, str] | None:
        if not isinstance(sha256, str) or not _SHA256.fullmatch(sha256):
            return None
        with self._uow_factory().read_only() as tx:
            row = tx.connection.execute(
                """SELECT v.object_key, v.mime, v.byte_size, v.sha256
                   FROM media_variants v
                   JOIN delivery_revisions r ON r.variant_id=v.id
                   JOIN deliveries d ON d.current_revision_id=r.id AND d.id=r.delivery_id
                   JOIN qc_reports q ON q.id=r.qc_report_id AND q.variant_id=v.id
                   WHERE v.sha256=? AND d.active=1 AND d.state NOT IN
                         ('CANCELLED','SUPERSEDED','FAILED_FINAL','EXPIRED')
                     AND v.qc_status IN ('PASS','REVIEW') AND q.decision IN ('PASS','REVIEW')
                   ORDER BY r.created_at DESC LIMIT 1""",
                (sha256,),
            ).fetchone()
        if row is None:
            return None
        with self._media_store.open(row["object_key"]) as stream:
            content = stream.read(5 * 1024 * 1024 + 1)
        if (
            not content
            or len(content) > 5 * 1024 * 1024
            or len(content) != int(row["byte_size"])
            or not hashlib.sha256(content).hexdigest() == sha256
            or row["mime"] != "image/jpeg"
        ):
            return None
        return content, str(row["mime"])


def _encode_cursor(scheduled_at_ms: int, delivery_id: str) -> str:
    return _encode_values((scheduled_at_ms, delivery_id))


def _decode_cursor(cursor: str | None) -> tuple[int, str] | None:
    return _decode_values(cursor, int)


def _encode_incident_cursor(last_seen_at_ms: int, incident_id: str) -> str:
    return _encode_values((last_seen_at_ms, incident_id))


def _decode_incident_cursor(cursor: str | None) -> tuple[int, str] | None:
    return _decode_values(cursor, int)


def _encode_candidate_cursor(created_at_ms: int, candidate_id: str) -> str:
    return _encode_values((created_at_ms, candidate_id))


def _decode_candidate_cursor(cursor: str | None) -> tuple[int, str] | None:
    return _decode_values(cursor, int)


def _encode_values(values: tuple[int, str]) -> str:
    raw = json.dumps(values, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_values(cursor: str | None, number_type: type[int]) -> tuple[int, str] | None:
    if cursor is None:
        return None
    if not cursor or len(cursor) > 256:
        raise ValueError("cursor is invalid")
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        value = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
        if not isinstance(value, list) or len(value) != 2:
            raise ValueError
        number = number_type(value[0])
        identifier = value[1]
        if not identifier or not isinstance(identifier, str):
            raise ValueError
        return number, identifier
    except (ValueError, TypeError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("cursor is invalid") from error
