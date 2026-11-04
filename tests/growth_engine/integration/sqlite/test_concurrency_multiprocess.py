from __future__ import annotations

import multiprocessing
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest

from growth_engine.adapters.outbound.persistence.sqlite.connection import connect
from growth_engine.adapters.outbound.persistence.sqlite.migrator import MigrationRunner
from growth_engine.adapters.outbound.persistence.sqlite.uow import (
    ConcurrencyConflict,
    SqliteUnitOfWork,
)
from growth_engine.domain.publishing.command import OutboxCommand


MIGRATIONS = Path("growth_engine/adapters/outbound/persistence/sqlite/migrations")
HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64
REPEATS = 20


def _prepare_database(path: Path, *, count: int, include_commands: bool) -> None:
    connection = connect(path)
    try:
        MigrationRunner(MIGRATIONS).apply(connection, application_version="pytest")
        connection.execute(
            """INSERT INTO channels
               (id, project_id, environment, channel_key, platform, remote_account_id, name, created_at)
               VALUES ('channel-main', 'venho-test', 'test', 'fb_hanoi', 'facebook',
                       'synthetic-page', 'Synthetic Page', 1)"""
        )
        connection.execute(
            """INSERT INTO channel_configs
               (id, channel_id, version, make_route_ref, graph_api_version, capability_json,
                config_hash, created_at)
               VALUES ('config-main', 'channel-main', 1, 'route-test', 'v21.0', '{}', ?, 1)""",
            (HASH_A,),
        )
        connection.execute(
            """INSERT INTO media_assets
               (id, source_type, source_ref, source_revision, source_sha256, original_key,
                metadata_json, created_at)
               VALUES ('asset-main', 'upload', 'synthetic', '1', ?, 'original.jpg', '{}', 1)""",
            (HASH_A,),
        )
        connection.execute(
            """INSERT INTO media_variants
               (id, asset_id, transform_version, sha256, object_key, width, height, mime,
                byte_size, qc_status, created_at)
               VALUES ('variant-main', 'asset-main', 'v1', ?, 'variant.jpg', 1200, 900,
                       'image/jpeg', 100, 'PASS', 1)""",
            (HASH_B,),
        )
        connection.execute(
            """INSERT INTO qc_reports
               (id, variant_id, caption_hash, ruleset_hash, fact_snapshot_hash, decision,
                result_json, created_at)
               VALUES ('qc-main', 'variant-main', ?, ?, ?, 'PASS', '{}', 1)""",
            (HASH_A, HASH_B, HASH_C),
        )

        for index in range(count):
            slot_id = f"slot-{index}"
            target_id = f"target-{index}"
            package_id = f"package-{index}"
            delivery_id = f"delivery-{index}"
            revision_id = f"revision-{index}"
            approval_id = f"approval-{index}"
            slot_day = (date(2026, 11, 5) + timedelta(days=index)).isoformat()
            connection.execute(
                """INSERT INTO slots
                   (id, project_id, local_date, local_time, timezone, lane, cadence_version,
                    scheduled_at, deadline_at, created_at)
                   VALUES (?, 'venho-test', ?, '09:00', 'Asia/Ho_Chi_Minh', 'weekly',
                           'v1', 10, 1000, 1)""",
                (slot_id, slot_day),
            )
            connection.execute(
                "INSERT INTO slot_targets(id, slot_id, channel_id) VALUES (?, ?, 'channel-main')",
                (target_id, slot_id),
            )
            connection.execute(
                """INSERT INTO content_packages
                   (id, slot_id, topic_key, pillar, lane, source_snapshot_json, fact_snapshot_json,
                    fact_snapshot_hash, generation_version, created_at)
                   VALUES (?, ?, 'topic', 'local', 'weekly', '{}', '{}', ?, 'v1', 1)""",
                (package_id, slot_id, HASH_A),
            )
            connection.execute(
                """INSERT INTO deliveries
                   (id, target_id, channel_id, package_id, state, created_at, updated_at)
                   VALUES (?, ?, 'channel-main', ?, 'DRAFT', 1, 1)""",
                (delivery_id, target_id, package_id),
            )
            payload_hash = f"{index + 1:064x}"
            connection.execute(
                """INSERT INTO delivery_revisions
                   (id, delivery_id, channel_id, revision_no, channel_config_id, variant_id,
                    qc_report_id, scheduled_at, deadline_at, caption, payload_json, payload_hash,
                    created_by, created_at)
                   VALUES (?, ?, 'channel-main', 1, 'config-main', 'variant-main', 'qc-main',
                           10, 1000, 'synthetic caption', '{}', ?, 'test', 1)""",
                (revision_id, delivery_id, payload_hash),
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
            if include_commands:
                connection.execute(
                    """INSERT INTO outbox_commands
                       (id, delivery_id, revision_id, sequence_no, kind, business_key, payload_hash,
                        state, dispatch_epoch, expires_at, next_attempt_at, created_at, updated_at)
                       VALUES (?, ?, ?, 1, 'PUBLISH', ?, ?, 'ACKED', 'epoch-test', 1000, 10, 1, 1)""",
                    (
                        f"command-{index}",
                        delivery_id,
                        revision_id,
                        f"publish:{delivery_id}:{revision_id}:1",
                        payload_hash,
                    ),
                )
    finally:
        connection.close()


def _race_worker(
    database_path: str,
    barrier,
    result_queue,
    operation: str,
    payload: dict[str, object],
) -> None:
    try:
        barrier.wait(timeout=20)
        uow = SqliteUnitOfWork(lambda: connect(database_path))
        with uow.begin_immediate() as tx:
            if operation == "insert_command":
                command = OutboxCommand.new(
                    command_id=str(payload["command_id"]),
                    delivery_id=str(payload["delivery_id"]),
                    revision_id=str(payload["revision_id"]),
                    sequence_no=1,
                    expires_at_ms=1_000,
                    now_ms=10,
                    envelope_token="synthetic-envelope",
                )
                tx.commands.save(
                    command,
                    payload_hash=str(payload["payload_hash"]),
                    dispatch_epoch="epoch-test",
                    created_at_ms=1,
                    updated_at_ms=1,
                )
                result_queue.put("inserted")
            elif operation == "authorize":
                try:
                    tx.cas_update(
                        "deliveries",
                        str(payload["delivery_id"]),
                        expected_row_version=1,
                        fields={"state": "EXECUTING", "updated_at": 20},
                    )
                except ConcurrencyConflict:
                    result_queue.put("conflict")
                    return
                tx.connection.execute(
                    """INSERT INTO executions
                       (id, command_id, delivery_id, principal_id, state, grant_id, authorized_at,
                        grant_expires_at, receipt_due_at, updated_at)
                       VALUES (?, ?, ?, 'test-principal', 'AUTHORIZED', ?, 20, 30, 40, 20)""",
                    (
                        str(payload["execution_id"]),
                        str(payload["command_id"]),
                        str(payload["delivery_id"]),
                        f"grant-{payload['execution_id']}",
                    ),
                )
                result_queue.put("authorized")
            elif operation == "update_slot":
                row = tx.connection.execute(
                    "SELECT row_version FROM slots WHERE id=?", (str(payload["slot_id"]),)
                ).fetchone()
                if payload["field"] == "cancelled_at":
                    fields = {"cancelled_at": 200}
                else:
                    fields = {"cancel_reason": "updated concurrently"}
                tx.cas_update(
                    "slots",
                    str(payload["slot_id"]),
                    expected_row_version=int(row[0]),
                    fields=fields,
                )
                result_queue.put("updated")
            else:
                raise AssertionError(f"unknown operation: {operation}")
    except sqlite3.IntegrityError:
        result_queue.put("duplicate")
    except BaseException as error:
        result_queue.put(f"error:{type(error).__name__}:{error}")
        raise


def _run_pair(
    context,
    database_path: Path,
    operation: str,
    first: dict[str, object],
    second: dict[str, object],
) -> list[str]:
    barrier = context.Barrier(2)
    result_queue = context.Queue()
    processes = [
        context.Process(target=_race_worker, args=(str(database_path), barrier, result_queue, operation, payload))
        for payload in (first, second)
    ]
    for process in processes:
        process.start()
    results = [result_queue.get(timeout=30) for _ in processes]
    for process in processes:
        process.join(timeout=30)
        assert process.exitcode == 0
    result_queue.close()
    result_queue.join_thread()
    return results


@pytest.mark.slow
def test_two_processes_cannot_enqueue_the_same_sequence_twenty_times(tmp_path: Path) -> None:
    database_path = tmp_path / "enqueue-races.db"
    _prepare_database(database_path, count=REPEATS, include_commands=False)
    context = multiprocessing.get_context("spawn")
    for index in range(REPEATS):
        delivery_id = f"delivery-{index}"
        revision_id = f"revision-{index}"
        payload_hash = f"{index + 1:064x}"
        results = _run_pair(
            context,
            database_path,
            "insert_command",
            {
                "command_id": f"command-{index}-a",
                "delivery_id": delivery_id,
                "revision_id": revision_id,
                "payload_hash": payload_hash,
            },
            {
                "command_id": f"command-{index}-b",
                "delivery_id": delivery_id,
                "revision_id": revision_id,
                "payload_hash": payload_hash,
            },
        )
        assert sorted(results) == ["duplicate", "inserted"]


@pytest.mark.slow
def test_two_processes_cas_authorize_one_execution_twenty_times(tmp_path: Path) -> None:
    database_path = tmp_path / "authorize-races.db"
    _prepare_database(database_path, count=REPEATS, include_commands=True)
    context = multiprocessing.get_context("spawn")
    for index in range(REPEATS):
        payload = {
            "delivery_id": f"delivery-{index}",
            "command_id": f"command-{index}",
        }
        results = _run_pair(
            context,
            database_path,
            "authorize",
            {**payload, "execution_id": f"execution-{index}-a"},
            {**payload, "execution_id": f"execution-{index}-b"},
        )
        assert sorted(results) == ["authorized", "conflict"]
        connection = connect(database_path)
        try:
            count = connection.execute(
                "SELECT count(*) FROM executions WHERE delivery_id=?", (payload["delivery_id"],)
            ).fetchone()[0]
            assert count == 1
        finally:
            connection.close()


@pytest.mark.slow
def test_two_process_updates_preserve_both_fields_and_row_version_twenty_times(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "update-races.db"
    _prepare_database(database_path, count=REPEATS, include_commands=False)
    context = multiprocessing.get_context("spawn")
    for index in range(REPEATS):
        slot_id = f"slot-{index}"
        results = _run_pair(
            context,
            database_path,
            "update_slot",
            {"slot_id": slot_id, "field": "cancelled_at"},
            {"slot_id": slot_id, "field": "cancel_reason"},
        )
        assert sorted(results) == ["updated", "updated"]
        connection = connect(database_path)
        try:
            row = connection.execute(
                "SELECT cancelled_at, cancel_reason, row_version FROM slots WHERE id=?", (slot_id,)
            ).fetchone()
            assert tuple(row) == (200, "updated concurrently", 3)
        finally:
            connection.close()
