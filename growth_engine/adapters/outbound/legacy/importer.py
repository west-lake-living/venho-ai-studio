from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import tempfile
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from growth_engine.adapters.outbound.persistence.sqlite.connection import connect
from growth_engine.adapters.outbound.persistence.sqlite.migrator import MigrationRunner


MIGRATIONS = Path(__file__).parents[1] / "persistence" / "sqlite" / "migrations"
FB_HANOI_PAGE_ID = "1124616474074140"
FB_CUTOVER_DATE = date(2026, 11, 3)
REQUIRED_FROM_P0 = "REQUIRED_FROM_P0"
_PLACEHOLDER_POST_ID = re.compile(r"^(?:\d+\.\s*)?post id$", re.IGNORECASE)
_CHANNELS = {
    "fb_hanoi": ("facebook", FB_HANOI_PAGE_ID, "Ven Hồ Hotel Hanoi"),
    "fb_venho": ("facebook", f"{REQUIRED_FROM_P0}:fb_venho", "Ven Hồ Hotel"),
    "ig_venho": ("instagram", f"{REQUIRED_FROM_P0}:ig_venho", "Ven Hồ Hotel Instagram"),
}


class LegacyImportError(ValueError):
    pass


@dataclass(frozen=True)
class _RawRecord:
    source_name: str
    source_key: str
    value: dict[str, Any]

    @property
    def raw_json(self) -> str:
        return _json(self.value)

    @property
    def raw_hash(self) -> str:
        return hashlib.sha256(self.raw_json.encode("utf-8")).hexdigest()


def dry_run_import(source_dir: str | Path, database_path: str | Path, report_path: str | Path) -> str:
    """Import legacy evidence into an isolated v2 database and write a redacted report."""
    source = Path(source_dir)
    if not source.is_dir():
        raise LegacyImportError("legacy import source must be a directory")
    database = Path(database_path)
    report = Path(report_path)
    records, slots = _load_source(source)
    if not records:
        raise LegacyImportError("legacy import source contains no JSON or SQLite records")

    connection = connect(database)
    try:
        MigrationRunner(MIGRATIONS).apply(connection, application_version="gc2-legacy-dry-run")
        connection.execute("BEGIN IMMEDIATE")
        for record in records:
            if _already_imported(connection, record):
                continue
            delivery_id, issue_code = _map_publication(connection, record, slots)
            connection.execute(
                """INSERT INTO legacy_imports
                   (source_name, source_key, raw_hash, raw_json, mapped_delivery_id,
                    issue_code, imported_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    record.source_name,
                    record.source_key,
                    record.raw_hash,
                    record.raw_json,
                    delivery_id,
                    issue_code,
                    0,
                ),
            )
        connection.commit()
        rendered = _render_report(connection, records)
    except BaseException:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()

    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(rendered, encoding="utf-8")
    return rendered


class LegacyImportDryRun:
    """CLI service: migration and import always happen in a disposable DB."""

    def run(self, source_dir: Path, report_path: Path) -> str:
        with tempfile.TemporaryDirectory(prefix="gc2-legacy-dry-run-") as directory:
            return dry_run_import(source_dir, Path(directory) / "legacy.sqlite", report_path)


def _load_source(source: Path) -> tuple[list[_RawRecord], dict[str, dict[str, Any]]]:
    records: list[_RawRecord] = []
    slots: dict[str, dict[str, Any]] = {}
    for path in sorted(item for item in source.rglob("*") if item.is_file()):
        relative = path.relative_to(source).as_posix()
        if path.suffix.casefold() == ".json":
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
                raise LegacyImportError(f"cannot read legacy JSON source {relative}") from error
            for index, row in enumerate(_json_rows(value), start=1):
                key = _record_key(row, index)
                source_name = "manual_post" if _is_manual(row) else relative
                record = _RawRecord(source_name, key, row)
                records.append(record)
                if _is_slot(row):
                    slots[key] = row
        elif path.suffix.casefold() in {".db", ".sqlite", ".sqlite3"}:
            for table, index, row in _sqlite_rows(path):
                key = _record_key(row, index)
                source_name = f"{relative}:{table}"
                records.append(_RawRecord(source_name, key, row))
                if _is_slot(row):
                    slots[key] = row
    return records, slots


def _json_rows(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)]
    if isinstance(value, dict):
        for key in ("publications", "records", "items"):
            rows = value.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
        return [value]
    return []


def _sqlite_rows(path: Path) -> list[tuple[str, int, dict[str, Any]]]:
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    output: list[tuple[str, int, dict[str, Any]]] = []
    try:
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        for table_row in tables:
            table = str(table_row[0])
            quoted_table = '"' + table.replace('"', '""') + '"'
            for index, row in enumerate(connection.execute(f"SELECT * FROM {quoted_table}"), start=1):
                output.append((table, index, {key: _json_value(row[key]) for key in row.keys()}))
    except sqlite3.Error as error:
        raise LegacyImportError(f"cannot read legacy SQLite source {path.name}") from error
    finally:
        connection.close()
    return output


def _record_key(row: dict[str, Any], index: int) -> str:
    for field in ("publication_id", "slot_id", "id", "candidate_id", "job_id"):
        value = row.get(field)
        if isinstance(value, (str, int)) and str(value).strip():
            return str(value)
    return f"row-{index:06d}"


def _is_slot(row: dict[str, Any]) -> bool:
    return isinstance(row.get("slot_id"), (str, int)) and bool(
        row.get("slot_date") or row.get("local_date")
    )


def _is_manual(row: dict[str, Any]) -> bool:
    values = (row.get("source_name"), row.get("source_type"), row.get("record_type"), row.get("origin"))
    return any(isinstance(value, str) and value.casefold() == "manual_post" for value in values)


def _already_imported(connection: sqlite3.Connection, record: _RawRecord) -> bool:
    return (
        connection.execute(
            """SELECT 1 FROM legacy_imports
               WHERE source_name=? AND source_key=? AND raw_hash=?""",
            (record.source_name, record.source_key, record.raw_hash),
        ).fetchone()
        is not None
    )


def _map_publication(
    connection: sqlite3.Connection,
    record: _RawRecord,
    slots: dict[str, dict[str, Any]],
) -> tuple[str | None, str | None]:
    row = record.value
    if _is_manual(row):
        return None, "MANUAL_POST_HISTORY"
    platform = str(row.get("platform", "")).casefold()
    if platform == "threads":
        return None, "THREADS_HISTORY_ONLY"
    if platform not in {"facebook", "instagram"}:
        return None, "UNSUPPORTED_PLATFORM"

    channel_key = _channel_key(row, platform)
    if channel_key is None:
        return None, "PAGE_ROUTE_UNRESOLVED"
    state, issue_code, post_id = _legacy_state(row, channel_key)

    slot_key_value = row.get("slot_id")
    if slot_key_value is None:
        return None, issue_code or "MISSING_SLOT_ID"
    slot_key = str(slot_key_value)
    slot = slots.get(slot_key)
    if slot is None or _parse_date(slot.get("slot_date") or slot.get("local_date")) is None:
        return None, issue_code or "SLOT_EVIDENCE_MISSING"

    _ensure_channel(connection, channel_key)
    slot_id = _ensure_slot(connection, slot_key, slot)
    target_id = _stable_id("target", f"{slot_id}:{channel_key}")
    connection.execute(
        "INSERT OR IGNORE INTO slot_targets (id, slot_id, channel_id) VALUES (?, ?, ?)",
        (target_id, slot_id, _stable_id("channel", channel_key)),
    )
    existing = connection.execute(
        "SELECT id FROM deliveries WHERE target_id=? AND active=1", (target_id,)
    ).fetchone()
    if existing is not None:
        return None, "DUPLICATE_SLOT_TARGET"

    package_id = _stable_id("package", f"{record.source_name}:{record.source_key}:{record.raw_hash}")
    fact_hash = hashlib.sha256(b"{}").hexdigest()
    snapshot = {
        "legacy_source": record.source_name,
        "legacy_source_key": record.source_key,
        "synthetic_placeholders": ["package facts/media/revision/approval not reconstructed"],
    }
    connection.execute(
        """INSERT INTO content_packages
           (id, slot_id, topic_key, pillar, lane, source_snapshot_json, fact_snapshot_json,
            fact_snapshot_hash, generation_version, created_at)
           VALUES (?, ?, ?, 'legacy', ?, ?, '{}', ?, 'legacy-import', 0)""",
        (
            package_id,
            slot_id,
            f"legacy:{_short_hash(record.source_key)}",
            str(slot.get("lane") or "legacy_import"),
            _json(snapshot),
            fact_hash,
        ),
    )
    delivery_id = _stable_id("delivery", f"{record.source_name}:{record.source_key}:{record.raw_hash}")
    now = _timestamp_ms(row.get("created_at"))
    connection.execute(
        """INSERT INTO deliveries
           (id, target_id, channel_id, package_id, state, origin, active,
            platform_post_id, permalink, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, 'legacy', ?, ?, ?, ?, ?)""",
        (
            delivery_id,
            target_id,
            _stable_id("channel", channel_key),
            package_id,
            state,
            0 if state == "SUPERSEDED" else 1,
            post_id,
            row.get("permalink") if isinstance(row.get("permalink"), str) else None,
            now,
            now,
        ),
    )
    return delivery_id, issue_code


def _channel_key(row: dict[str, Any], platform: str) -> str | None:
    explicit = row.get("channel_key")
    if explicit in _CHANNELS:
        return str(explicit)
    if platform == "instagram":
        return "ig_venho"

    page_id = str(row.get("page_id") or row.get("remote_account_id") or "")
    post_id = str(row.get("platform_post_id") or "")
    if page_id == FB_HANOI_PAGE_ID or post_id.startswith(f"{FB_HANOI_PAGE_ID}_"):
        return "fb_hanoi"
    event_date = _parse_date(row.get("published_at") or row.get("created_at"))
    if event_date is None:
        return None
    # §12.1 and T0-05 identify post-cutover, otherwise-untracked Facebook as fb_venho.
    return "fb_hanoi" if event_date < FB_CUTOVER_DATE else "fb_venho"


def _ensure_channel(connection: sqlite3.Connection, channel_key: str) -> None:
    platform, account_id, name = _CHANNELS[channel_key]
    connection.execute(
        """INSERT OR IGNORE INTO channels
           (id, project_id, environment, channel_key, platform, remote_account_id, name,
            enabled, paused, created_at)
           VALUES (?, 'venho_hotel', 'test', ?, ?, ?, ?, 0, 0, 0)""",
        (_stable_id("channel", channel_key), channel_key, platform, account_id, name),
    )


def _ensure_slot(connection: sqlite3.Connection, source_slot_id: str, slot: dict[str, Any]) -> str:
    slot_id = _stable_id("slot", source_slot_id)
    existing = connection.execute("SELECT id FROM slots WHERE id=?", (slot_id,)).fetchone()
    if existing is not None:
        return slot_id
    local_date = _parse_date(slot.get("slot_date") or slot.get("local_date"))
    if local_date is None:
        raise LegacyImportError("slot date became unavailable during mapping")
    local_time = slot.get("local_time") or slot.get("slot_time")
    lane = str(slot.get("lane") or "legacy_import")
    if not local_time:
        local_time = "00:00"
        lane = f"{lane}:time-unknown:{_short_hash(source_slot_id)}"
    matching = connection.execute(
        """SELECT id FROM slots
           WHERE project_id='venho_hotel' AND local_date=? AND local_time=? AND lane=?""",
        (local_date.isoformat(), str(local_time), lane),
    ).fetchone()
    if matching is not None:
        return str(matching[0])
    connection.execute(
        """INSERT INTO slots
           (id, project_id, local_date, local_time, timezone, lane, cadence_version,
            scheduled_at, deadline_at, created_at)
           VALUES (?, 'venho_hotel', ?, ?, 'Asia/Ho_Chi_Minh', ?, 'legacy', 0, 0, 0)""",
        (slot_id, local_date.isoformat(), str(local_time), lane),
    )
    return slot_id


def _legacy_state(row: dict[str, Any], channel_key: str) -> tuple[str, str | None, str | None]:
    status = str(row.get("status", "")).upper()
    post_id_value = row.get("platform_post_id")
    post_id = str(post_id_value).strip() if post_id_value is not None else ""
    if status == "GATEWAY_ACCEPTED":
        return "LEGACY_UNVERIFIED", "CLOSED_UNRESOLVED", None
    if status == "PUBLISHED":
        if not post_id:
            return "LEGACY_UNVERIFIED", "MISSING_POST_ID", None
        if _PLACEHOLDER_POST_ID.fullmatch(post_id):
            return "LEGACY_UNVERIFIED", "PLACEHOLDER_POST_ID", None
        issue = "UNTRACKED_PAGE" if channel_key == "fb_venho" else "POST_UNVERIFIED"
        return "LEGACY_UNVERIFIED", issue, post_id
    if status in {"APPROVED_SCHEDULED", "PENDING_APPROVAL", "STALE_APPROVAL"}:
        return "IN_REVIEW", "APPROVAL_NOT_RESTORED", None
    if status == "SUPERSEDED":
        return "SUPERSEDED", None, None
    if status == "CANCELLED":
        return "CANCELLED", None, None
    if status in {"FAILED", "REJECTED"}:
        return "FAILED_FINAL", "LEGACY_FAILURE_UNCLASSIFIED", None
    if status == "DISABLED":
        return "BLOCKED", "LEGACY_CHANNEL_DISABLED", None
    return "LEGACY_UNVERIFIED", "LEGACY_STATE_UNMAPPED", None


def _render_report(connection: sqlite3.Connection, current_records: list[_RawRecord]) -> str:
    before: Counter[tuple[str, str]] = Counter()
    after: Counter[tuple[str, str]] = Counter()
    issues: Counter[str] = Counter()
    mismatches: list[tuple[str, str, str, str]] = []
    for record in current_records:
        legacy_status = str(record.value.get("status") or "UNSPECIFIED").upper()
        before[(record.source_name, legacy_status)] += 1
        stored = connection.execute(
            """SELECT i.mapped_delivery_id, i.issue_code, d.state, d.channel_id
               FROM legacy_imports i LEFT JOIN deliveries d ON d.id=i.mapped_delivery_id
               WHERE i.source_name=? AND i.source_key=? AND i.raw_hash=?""",
            (record.source_name, record.source_key, record.raw_hash),
        ).fetchone()
        after_state = str(stored["state"] or "HISTORY_ONLY") if stored is not None else "NOT_IMPORTED"
        after[(record.source_name, after_state)] += 1
        issue = str(stored["issue_code"] or "") if stored is not None else "NOT_IMPORTED"
        if issue:
            issues[issue] += 1
            channel_key = ""
            if stored["channel_id"]:
                channel = connection.execute(
                    "SELECT channel_key FROM channels WHERE id=?", (stored["channel_id"],)
                ).fetchone()
                channel_key = str(channel[0]) if channel else ""
            mismatches.append((record.source_name, record.source_key, channel_key or "—", issue))

    lines = [
        "# GC2 legacy import dry-run",
        "",
        "Only a disposable v2 database was written. Source files were read-only; no approvals were recreated.",
        "",
        f"- Raw rows in current source: {len(current_records)}",
        f"- Rows recorded in `legacy_imports`: {connection.execute('SELECT count(*) FROM legacy_imports').fetchone()[0]}",
        f"- Delivery rows in dry-run database: {connection.execute('SELECT count(*) FROM deliveries').fetchone()[0]}",
        "- Page ID placeholders: fb_venho and ig_venho remain `REQUIRED_FROM_P0`; their channels are disabled.",
        "",
        "## Source × legacy status before import",
        "",
        "| Source | Legacy status | Rows |",
        "|---|---|---:|",
    ]
    for (source, status), count in sorted(before.items()):
        lines.append(f"| `{source}` | `{status}` | {count} |")
    lines.extend(["", "## Source × state after mapping", "", "| Source | Dry-run state | Rows |", "|---|---|---:|"])
    for (source, state), count in sorted(after.items()):
        lines.append(f"| `{source}` | `{state}` | {count} |")
    lines.extend(["", "## Issue codes", "", "| Issue code | Rows |", "|---|---:|"])
    if issues:
        for issue, count in sorted(issues.items()):
            lines.append(f"| `{issue}` | {count} |")
    else:
        lines.append("| None | 0 |")
    lines.extend(["", "## Mismatches and unresolved mappings", "", "| Source | Key | Target | Issue |", "|---|---|---|---|"])
    if mismatches:
        for source, key, target, issue in sorted(mismatches):
            lines.append(f"| `{source}` | `{key}` | `{target}` | `{issue}` |")
    else:
        lines.append("| None | — | — | — |")
    lines.append("")
    return "\n".join(lines)


def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            return None


def _timestamp_ms(value: Any) -> int:
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, str):
        try:
            return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)
        except ValueError:
            pass
    return 0


def _stable_id(kind: str, value: str) -> str:
    return f"legacy-{kind}-{_short_hash(value)}"


def _short_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _json_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"$binary_hex": value.hex()}
    if isinstance(value, sqlite3.Row):
        return {key: _json_value(value[key]) for key in value.keys()}
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return value
