from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest

from growth_engine.adapters.outbound.persistence.sqlite.connection import connect
from growth_engine.adapters.outbound.persistence.sqlite.migrator import MigrationRunner


MIGRATIONS = Path("growth_engine/adapters/outbound/persistence/sqlite/migrations")
HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64

# All database rows and identifiers below are synthetic test data.


def _insert_command(
    connection: sqlite3.Connection,
    command_id: str,
    delivery_id: str,
    revision_id: str,
    *,
    sequence_no: int,
    state: str,
    payload_hash: str | None = None,
) -> None:
    if payload_hash is None:
        row = connection.execute(
            "SELECT payload_hash FROM delivery_revisions WHERE id=?", (revision_id,)
        ).fetchone()
        if row is None:
            raise AssertionError(f"missing seeded revision: {revision_id}")
        payload_hash = str(row[0])
    connection.execute(
        """INSERT INTO outbox_commands
           (id, delivery_id, revision_id, sequence_no, kind, business_key, payload_hash,
            state, dispatch_epoch, expires_at, next_attempt_at, created_at, updated_at)
           VALUES (?, ?, ?, ?, 'PUBLISH', ?, ?, ?, 'test-epoch', 500, 100, 1, 1)""",
        (
            command_id,
            delivery_id,
            revision_id,
            sequence_no,
            f"publish:{delivery_id}:{revision_id}:{sequence_no}",
            payload_hash,
            state,
        ),
    )


def _insert_execution(
    connection: sqlite3.Connection,
    execution_id: str,
    command_id: str,
    delivery_id: str,
    state: str,
) -> None:
    connection.execute(
        """INSERT INTO executions
           (id, command_id, delivery_id, principal_id, state, grant_id, authorized_at,
            grant_expires_at, receipt_due_at, updated_at)
           VALUES (?, ?, ?, 'test-principal', ?, ?, 100, 200, 300, 100)""",
        (execution_id, command_id, delivery_id, state, f"grant-{execution_id}"),
    )


def _insert_receipt(connection: sqlite3.Connection, receipt_id: str) -> None:
    connection.execute(
        """INSERT INTO receipt_inbox
           (id, issuer_id, event_id, execution_id, event_hash, body_json, received_at,
            processing_state, quarantine_reason)
           VALUES (?, 'test-issuer', 'grant-unknown:reported', 'unknown-execution', ?, '{}',
                   100, 'QUARANTINED', 'unknown execution')""",
        (receipt_id, HASH_A),
    )


def _reject_second_active_delivery(connection: sqlite3.Connection) -> None:
    connection.execute(
        """INSERT INTO deliveries
           (id, target_id, channel_id, package_id, state, created_at, updated_at)
           VALUES ('delivery-extra', 'target-hanoi', 'channel-hanoi', 'package-hanoi',
                   'DRAFT', 1, 1)"""
    )


def _reject_delivery_target_channel_mismatch(connection: sqlite3.Connection) -> None:
    connection.execute(
        """INSERT INTO deliveries
           (id, target_id, channel_id, package_id, state, active, created_at, updated_at)
           VALUES ('delivery-mismatch', 'target-hanoi', 'channel-venho', 'package-hanoi',
                   'SUPERSEDED', 0, 1, 1)"""
    )


def _reject_revision_update(connection: sqlite3.Connection) -> None:
    connection.execute("UPDATE delivery_revisions SET caption='changed' WHERE id='revision-hanoi'")


def _reject_approval_wrong_hash(connection: sqlite3.Connection) -> None:
    connection.execute(
        """INSERT INTO approval_decisions
           (id, revision_id, payload_hash, decision, actor_id, created_at)
           VALUES ('approval-wrong', 'revision-hanoi', ?, 'APPROVE', 'test', 1)""",
        (HASH_C,),
    )


def _reject_revision_from_another_delivery(connection: sqlite3.Connection) -> None:
    connection.execute(
        "UPDATE deliveries SET current_revision_id='revision-venho' WHERE id='delivery-hanoi'"
    )


def _reject_published_without_post_id(connection: sqlite3.Connection) -> None:
    connection.execute(
        "UPDATE deliveries SET state='PUBLISHED', platform_post_id=NULL WHERE id='delivery-venho'"
    )


def _reject_superseded_active_delivery(connection: sqlite3.Connection) -> None:
    connection.execute("UPDATE deliveries SET state='SUPERSEDED' WHERE id='delivery-hanoi'")


def _reject_remote_account_change(connection: sqlite3.Connection) -> None:
    connection.execute(
        "UPDATE channels SET remote_account_id='changed-page-id' WHERE id='channel-hanoi'"
    )


def _reject_threads_channel(connection: sqlite3.Connection) -> None:
    connection.execute(
        """INSERT INTO channels
           (id, project_id, environment, channel_key, platform, remote_account_id, name, created_at)
           VALUES ('channel-threads', 'venho', 'test', 'threads_test', 'threads',
                   'thread-id', 'Threads', 1)"""
    )


def _reject_duplicate_channel_key(connection: sqlite3.Connection) -> None:
    connection.execute(
        """INSERT INTO channels
           (id, project_id, environment, channel_key, platform, remote_account_id, name, created_at)
           VALUES ('channel-duplicate', 'venho', 'test', 'fb_hanoi', 'facebook',
                   'different-page-id', 'duplicate', 1)"""
    )


def _reject_variant_bytes_update(connection: sqlite3.Connection) -> None:
    connection.execute("UPDATE media_variants SET sha256=? WHERE id='variant-main'", (HASH_C,))


def _reject_second_open_command(connection: sqlite3.Connection) -> None:
    _insert_command(connection, "command-1", "delivery-hanoi", "revision-hanoi", sequence_no=1, state="PENDING")
    _insert_command(connection, "command-2", "delivery-hanoi", "revision-hanoi", sequence_no=2, state="PENDING")


def _reject_command_hash_mismatch(connection: sqlite3.Connection) -> None:
    _insert_command(
        connection,
        "command-hash-mismatch",
        "delivery-hanoi",
        "revision-hanoi",
        sequence_no=1,
        state="PENDING",
        payload_hash=HASH_C,
    )


def _reject_second_live_execution_across_commands(connection: sqlite3.Connection) -> None:
    _insert_command(connection, "command-1", "delivery-hanoi", "revision-hanoi", sequence_no=1, state="CANCELLED")
    _insert_command(connection, "command-2", "delivery-hanoi", "revision-hanoi", sequence_no=2, state="CANCELLED")
    _insert_execution(connection, "execution-1", "command-1", "delivery-hanoi", "UNKNOWN")
    _insert_execution(connection, "execution-2", "command-2", "delivery-hanoi", "AUTHORIZED")


def _reject_execution_for_another_delivery(connection: sqlite3.Connection) -> None:
    _insert_command(connection, "command-1", "delivery-hanoi", "revision-hanoi", sequence_no=1, state="CANCELLED")
    _insert_execution(connection, "execution-wrong-delivery", "command-1", "delivery-venho", "AUTHORIZED")


def _reject_duplicate_receipt_event(connection: sqlite3.Connection) -> None:
    _insert_receipt(connection, "receipt-1")
    _insert_receipt(connection, "receipt-2")


def _reject_duplicate_post_on_same_page(connection: sqlite3.Connection) -> None:
    connection.execute(
        "UPDATE deliveries SET state='PUBLISHED', platform_post_id='same-post' WHERE id='delivery-hanoi'"
    )
    connection.execute(
        "UPDATE deliveries SET state='PUBLISHED', platform_post_id='same-post' WHERE id='delivery-hanoi-2'"
    )


def _reject_duplicate_open_incident(connection: sqlite3.Connection) -> None:
    for incident_id in ("incident-1", "incident-2"):
        connection.execute(
            """INSERT INTO incidents
               (id, fingerprint, type, severity, state, first_seen_at, last_seen_at,
                occurrence_count, details_json)
               VALUES (?, 'delivery:error', 'delivery', 'WARNING', 'OPEN', 1, 1, 1, '{}')""",
            (incident_id,),
        )


def _reject_nonzero_zero_metric(connection: sqlite3.Connection) -> None:
    connection.execute(
        """INSERT INTO metric_observations
           (id, delivery_id, metric, checkpoint, observed_at, post_age_seconds, value,
            value_state, source, api_version)
           VALUES ('metric-invalid', 'delivery-hanoi', 'reach', '24h', 100, 100, 7,
                   'ZERO', 'mock', 'v1')"""
    )


def _reject_audit_update(connection: sqlite3.Connection) -> None:
    connection.execute(
        """INSERT INTO audit_events
           (id, aggregate_type, aggregate_id, actor, action, correlation_id, created_at)
           VALUES ('audit-1', 'delivery', 'delivery-hanoi', 'test', 'create', 'corr-1', 1)"""
    )
    connection.execute("UPDATE audit_events SET actor='changed' WHERE id='audit-1'")


def _reject_revision_delivery_channel_mismatch(connection: sqlite3.Connection) -> None:
    connection.execute(
        """INSERT INTO delivery_revisions
           (id, delivery_id, channel_id, revision_no, channel_config_id, variant_id, qc_report_id,
            scheduled_at, deadline_at, caption, payload_json, payload_hash, created_by, created_at)
           VALUES ('revision-mismatch', 'delivery-hanoi', 'channel-venho', 2, 'config-venho',
                   'variant-main', 'qc-main', 100, 200, 'caption', '{}', ?, 'test', 1)""",
        (HASH_C,),
    )


CONSTRAINT_CASES: tuple[tuple[str, Callable[[sqlite3.Connection], None]], ...] = (
    ("second active delivery for target", _reject_second_active_delivery),
    ("delivery target/channel mismatch", _reject_delivery_target_channel_mismatch),
    ("revision is immutable", _reject_revision_update),
    ("approval payload hash mismatch", _reject_approval_wrong_hash),
    ("revision belongs to another delivery", _reject_revision_from_another_delivery),
    ("published requires platform post id", _reject_published_without_post_id),
    ("superseded must be inactive", _reject_superseded_active_delivery),
    ("channel remote identity is immutable", _reject_remote_account_change),
    ("unsupported Threads platform", _reject_threads_channel),
    ("channel key is unique per environment", _reject_duplicate_channel_key),
    ("variant bytes are immutable", _reject_variant_bytes_update),
    ("only one open command per delivery", _reject_second_open_command),
    ("command hash must match revision", _reject_command_hash_mismatch),
    ("only one live execution per delivery across commands", _reject_second_live_execution_across_commands),
    ("execution must match command delivery", _reject_execution_for_another_delivery),
    ("receipt event is unique per issuer", _reject_duplicate_receipt_event),
    ("platform post id is unique per page", _reject_duplicate_post_on_same_page),
    ("only one open incident per fingerprint", _reject_duplicate_open_incident),
    ("ZERO metric requires value zero", _reject_nonzero_zero_metric),
    ("audit log is append-only", _reject_audit_update),
    ("revision channel must match delivery channel", _reject_revision_delivery_channel_mismatch),
)


@pytest.fixture
def database(tmp_path: Path) -> sqlite3.Connection:
    connection = connect(tmp_path / "constraints.db")
    try:
        runner = MigrationRunner(MIGRATIONS)
        runner.apply(connection, application_version="pytest")
        assert runner.check(connection) == (1, 2, 3, 4, 5, 6, 7, 9)
        _seed_valid_graph(connection)
        yield connection
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        connection.close()


def _seed_valid_graph(connection: sqlite3.Connection) -> None:
    channels = (
        ("channel-hanoi", "fb_hanoi", "facebook", "page-test-hanoi", "Ven Ho Hotel Hanoi"),
        ("channel-venho", "fb_venho", "facebook", "page-venho", "Ven Ho Hotel"),
        ("channel-ig", "ig_venho", "instagram", "ig-venho", "Ven Ho Instagram"),
    )
    for channel_id, channel_key, platform, remote_id, name in channels:
        connection.execute(
            """INSERT INTO channels
               (id, project_id, environment, channel_key, platform, remote_account_id, name, created_at)
               VALUES (?, 'venho', 'test', ?, ?, ?, ?, 1)""",
            (channel_id, channel_key, platform, remote_id, name),
        )
        config_id = f"config-{channel_id.removeprefix('channel-')}"
        connection.execute(
            """INSERT INTO channel_configs
               (id, channel_id, version, make_route_ref, graph_api_version, capability_json,
                config_hash, created_at)
               VALUES (?, ?, 1, 'scenario-test', 'v21.0', '{}', ?, 1)""",
            (config_id, channel_id, HASH_A),
        )

    connection.executemany(
        """INSERT INTO slots
           (id, project_id, local_date, local_time, timezone, lane, cadence_version,
            scheduled_at, deadline_at, created_at)
           VALUES (?, 'venho', ?, '10:00', 'Asia/Ho_Chi_Minh', 'weekly', 'v1', 100, 200, 1)""",
        (("slot-main", "2026-11-05"), ("slot-second", "2026-11-06")),
    )
    targets = (
        ("target-hanoi", "slot-main", "channel-hanoi"),
        ("target-venho", "slot-main", "channel-venho"),
        ("target-ig", "slot-main", "channel-ig"),
        ("target-hanoi-2", "slot-second", "channel-hanoi"),
    )
    for target_id, slot_id, channel_id in targets:
        connection.execute(
            "INSERT INTO slot_targets(id, slot_id, channel_id) VALUES (?, ?, ?)",
            (target_id, slot_id, channel_id),
        )

    deliveries = (
        ("delivery-hanoi", "target-hanoi", "channel-hanoi", "package-hanoi", "slot-main"),
        ("delivery-venho", "target-venho", "channel-venho", "package-venho", "slot-main"),
        ("delivery-ig", "target-ig", "channel-ig", "package-ig", "slot-main"),
        ("delivery-hanoi-2", "target-hanoi-2", "channel-hanoi", "package-hanoi-2", "slot-second"),
    )
    for delivery_id, target_id, channel_id, package_id, slot_id in deliveries:
        connection.execute(
            """INSERT INTO content_packages
               (id, slot_id, topic_key, pillar, lane, source_snapshot_json, fact_snapshot_json,
                fact_snapshot_hash, generation_version, created_at)
               VALUES (?, ?, 'topic', 'local', 'weekly', '{}', '{}', ?, 'test-v1', 1)""",
            (package_id, slot_id, HASH_A),
        )
        connection.execute(
            """INSERT INTO deliveries
               (id, target_id, channel_id, package_id, state, created_at, updated_at)
               VALUES (?, ?, ?, ?, 'DRAFT', 1, 1)""",
            (delivery_id, target_id, channel_id, package_id),
        )

    connection.execute(
        """INSERT INTO media_assets
           (id, source_type, source_ref, source_revision, source_sha256, original_key,
            metadata_json, created_at)
           VALUES ('asset-main', 'upload', 'test-source', '1', ?, 'test/original.jpg', '{}', 1)""",
        (HASH_A,),
    )
    connection.execute(
        """INSERT INTO media_variants
           (id, asset_id, transform_version, sha256, object_key, width, height, mime,
            byte_size, qc_status, created_at)
           VALUES ('variant-main', 'asset-main', 'v1', ?, 'test/variant.jpg', 1200, 900,
                   'image/jpeg', 1024, 'PASS', 1)""",
        (HASH_B,),
    )
    connection.execute(
        """INSERT INTO qc_reports
           (id, variant_id, caption_hash, ruleset_hash, fact_snapshot_hash, decision,
            result_json, created_at)
           VALUES ('qc-main', 'variant-main', ?, ?, ?, 'PASS', '{}', 1)""",
        (HASH_A, HASH_B, HASH_C),
    )

    revision_approval = (
        ("delivery-hanoi", "channel-hanoi", "revision-hanoi", "approval-hanoi"),
        ("delivery-venho", "channel-venho", "revision-venho", "approval-venho"),
        ("delivery-ig", "channel-ig", "revision-ig", "approval-ig"),
        ("delivery-hanoi-2", "channel-hanoi", "revision-hanoi-2", "approval-hanoi-2"),
    )
    for index, (delivery_id, channel_id, revision_id, approval_id) in enumerate(revision_approval, start=1):
        config_id = f"config-{channel_id.removeprefix('channel-')}"
        payload_hash = f"{index:064x}"
        connection.execute(
            """INSERT INTO delivery_revisions
               (id, delivery_id, channel_id, revision_no, channel_config_id, variant_id,
                qc_report_id, scheduled_at, deadline_at, caption, payload_json, payload_hash,
                created_by, created_at)
               VALUES (?, ?, ?, 1, ?, 'variant-main', 'qc-main', 100, 200, 'caption', '{}', ?,
                       'test', 1)""",
            (revision_id, delivery_id, channel_id, config_id, payload_hash),
        )
        connection.execute(
            """INSERT INTO approval_decisions
               (id, revision_id, payload_hash, decision, actor_id, created_at)
               VALUES (?, ?, ?, 'APPROVE', 'test', 1)""",
            (approval_id, revision_id, payload_hash),
        )
        connection.execute(
            """UPDATE deliveries
               SET state='APPROVED', current_revision_id=?, active_approval_id=?
               WHERE id=?""",
            (revision_id, approval_id, delivery_id),
        )


@pytest.mark.parametrize(
    "reject",
    [pytest.param(operation, id=name) for name, operation in CONSTRAINT_CASES],
)
def test_schema_rejects_each_documented_violation(
    database: sqlite3.Connection,
    reject: Callable[[sqlite3.Connection], None],
) -> None:
    with pytest.raises(sqlite3.IntegrityError, match=".+"):
        reject(database)


def test_accepted_slot_fanout_and_safe_retry_after_no_side_effect(
    database: sqlite3.Connection,
) -> None:
    rows = database.execute(
        """SELECT d.id, d.channel_id, d.current_revision_id, d.active_approval_id
           FROM deliveries d JOIN slot_targets t ON t.id=d.target_id
           WHERE t.slot_id='slot-main' ORDER BY d.channel_id"""
    ).fetchall()
    assert len(rows) == 3
    assert len({row["channel_id"] for row in rows}) == 3
    assert all(row["current_revision_id"] and row["active_approval_id"] for row in rows)
    _insert_command(database, "command-1", "delivery-hanoi", "revision-hanoi", sequence_no=1, state="AUTHORIZED")
    _insert_execution(database, "execution-1", "command-1", "delivery-hanoi", "NO_SIDE_EFFECT")
    _insert_command(database, "command-2", "delivery-hanoi", "revision-hanoi", sequence_no=2, state="PENDING")
    _insert_execution(database, "execution-2", "command-2", "delivery-hanoi", "AUTHORIZED")
    rows = database.execute(
        "SELECT state FROM executions WHERE delivery_id='delivery-hanoi' ORDER BY id"
    ).fetchall()
    assert [row[0] for row in rows] == ["NO_SIDE_EFFECT", "AUTHORIZED"]


def test_unmatched_receipt_is_accepted_as_quarantined_evidence(database: sqlite3.Connection) -> None:
    _insert_receipt(database, "receipt-unmatched")
    row = database.execute(
        "SELECT execution_id, processing_state FROM receipt_inbox WHERE id='receipt-unmatched'"
    ).fetchone()
    assert tuple(row) == ("unknown-execution", "QUARANTINED")
