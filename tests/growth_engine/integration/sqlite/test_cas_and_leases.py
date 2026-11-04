from __future__ import annotations

from pathlib import Path

from growth_engine.adapters.outbound.persistence.sqlite.connection import connect
from growth_engine.adapters.outbound.persistence.sqlite.migrator import MigrationRunner
from growth_engine.adapters.outbound.persistence.sqlite.uow import SqliteUnitOfWork
from growth_engine.adapters.outbound.persistence.sqlite.repositories.jobs import JobRecord
from growth_engine.domain.publishing.command import OutboxCommand


MIGRATIONS = Path("growth_engine/adapters/outbound/persistence/sqlite/migrations")
HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64


def _database(tmp_path: Path) -> tuple[Path, SqliteUnitOfWork]:
    path = tmp_path / "leases.db"
    connection = connect(path)
    try:
        MigrationRunner(MIGRATIONS).apply(connection, application_version="pytest")
    finally:
        connection.close()
    return path, SqliteUnitOfWork(lambda: connect(path), sleep=lambda _: None)


def test_old_lease_token_cannot_complete_after_reclaim(tmp_path: Path) -> None:
    _path, uow = _database(tmp_path)
    with uow.begin_immediate() as tx:
        tx.jobs.save(
            JobRecord(
                id="job-a",
                kind="generate",
                lane="jobs",
                business_key="generate:synthetic-a",
                payload_json='{"synthetic":true}',
                state="PENDING",
                run_at_ms=10,
                created_at_ms=1,
                updated_at_ms=1,
            )
        )
        first = tx.jobs.claim_with_lease(
            {"id": "job-a", "state": "PENDING"}, owner="worker-a", lease_ms=100, now_ms=10
        )
        assert first is not None
        _first_row, first_token = first

        reclaimed = tx.jobs.claim_with_lease(
            {
                "id": "job-a",
                "state": "RUNNING",
                "lease_until": ("<=", 110),
            },
            owner="worker-b",
            lease_ms=100,
            now_ms=111,
        )
        assert reclaimed is not None
        _reclaimed_row, second_token = reclaimed
        assert second_token != first_token
        assert tx.jobs.complete("job-a", first_token, updated_at_ms=112) is False
        still_owned = tx.jobs.get("job-a")
        assert still_owned is not None
        assert still_owned.lease_token == second_token
        assert still_owned.state == "RUNNING"
        assert tx.jobs.complete("job-a", second_token, updated_at_ms=113) is True
        completed = tx.jobs.get("job-a")
        assert completed is not None and completed.state == "SUCCEEDED"
        assert completed.lease_token is None


def test_command_claim_uses_single_gate_and_fencing_token(tmp_path: Path) -> None:
    _path, uow = _database(tmp_path)
    command = OutboxCommand.new(
        command_id="command-a",
        delivery_id="delivery-a",
        revision_id="revision-a",
        sequence_no=1,
        expires_at_ms=1_000,
        now_ms=10,
        envelope_token="synthetic-envelope",
    )
    with uow.begin_immediate() as tx:
        connection = tx.connection
        connection.execute(
            """INSERT INTO channels
               (id, project_id, environment, channel_key, platform, remote_account_id, name, created_at)
               VALUES ('channel-a', 'test-project', 'test', 'fb_hanoi', 'facebook',
                       'synthetic-page', 'Synthetic Page', 1)"""
        )
        connection.execute(
            """INSERT INTO channel_configs
               (id, channel_id, version, make_route_ref, graph_api_version, capability_json,
                config_hash, created_at)
               VALUES ('config-a', 'channel-a', 1, 'route-test', 'v21.0', '{}', ?, 1)""",
            (HASH_A,),
        )
        connection.execute(
            """INSERT INTO slots
               (id, project_id, local_date, local_time, timezone, lane, cadence_version,
                scheduled_at, deadline_at, created_at)
               VALUES ('slot-a', 'test-project', '2026-11-05', '09:00', 'Asia/Ho_Chi_Minh',
                       'weekly', 'v1', 10, 1000, 1)"""
        )
        connection.execute(
            "INSERT INTO slot_targets(id, slot_id, channel_id) VALUES ('target-a', 'slot-a', 'channel-a')"
        )
        connection.execute(
            """INSERT INTO content_packages
               (id, slot_id, topic_key, pillar, lane, source_snapshot_json, fact_snapshot_json,
                fact_snapshot_hash, generation_version, created_at)
               VALUES ('package-a', 'slot-a', 'topic', 'local', 'weekly', '{}', '{}', ?, 'v1', 1)""",
            (HASH_A,),
        )
        connection.execute(
            """INSERT INTO media_assets
               (id, source_type, source_ref, source_revision, source_sha256, original_key,
                metadata_json, created_at)
               VALUES ('asset-a', 'upload', 'synthetic', '1', ?, 'original.jpg', '{}', 1)""",
            (HASH_A,),
        )
        connection.execute(
            """INSERT INTO media_variants
               (id, asset_id, transform_version, sha256, object_key, width, height, mime,
                byte_size, qc_status, created_at)
               VALUES ('variant-a', 'asset-a', 'v1', ?, 'variant.jpg', 1200, 900,
                       'image/jpeg', 100, 'PASS', 1)""",
            (HASH_B,),
        )
        connection.execute(
            """INSERT INTO qc_reports
               (id, variant_id, caption_hash, ruleset_hash, fact_snapshot_hash, decision,
                result_json, created_at)
               VALUES ('qc-a', 'variant-a', ?, ?, ?, 'PASS', '{}', 1)""",
            (HASH_A, HASH_B, HASH_A),
        )
        connection.execute(
            """INSERT INTO deliveries
               (id, target_id, channel_id, package_id, state, created_at, updated_at)
               VALUES ('delivery-a', 'target-a', 'channel-a', 'package-a', 'DRAFT', 1, 1)"""
        )
        connection.execute(
            """INSERT INTO delivery_revisions
               (id, delivery_id, channel_id, revision_no, channel_config_id, variant_id,
                qc_report_id, scheduled_at, deadline_at, caption, payload_json, payload_hash,
                created_by, created_at)
               VALUES ('revision-a', 'delivery-a', 'channel-a', 1, 'config-a', 'variant-a',
                       'qc-a', 10, 1000, 'caption', '{}', ?, 'test', 1)""",
            (HASH_C,),
        )
        tx.commands.save(
            command,
            payload_hash=HASH_C,
            dispatch_epoch="epoch-test",
            created_at_ms=1,
            updated_at_ms=1,
        )

        first = tx.commands.claim_with_lease(
            {"id": command.id, "state": "PENDING"},
            owner="publish-a",
            lease_ms=100,
            now_ms=10,
        )
        assert first is not None
        _first_row, first_token = first
        reclaimed = tx.commands.claim_with_lease(
            {"id": command.id, "state": "DELIVERING", "lease_until": ("<=", 110)},
            owner="publish-b",
            lease_ms=100,
            now_ms=111,
        )
        assert reclaimed is not None
        _reclaimed_row, second_token = reclaimed
        assert second_token != first_token
        assert not tx.commands.complete(
            command.id, first_token, acked_at_ms=112, updated_at_ms=112
        )
        assert tx.commands.complete(
            command.id, second_token, acked_at_ms=113, updated_at_ms=113
        )
        saved = tx.commands.get(command.id, envelope_token=command.envelope_token)
        assert saved is not None and saved.state.value == "ACKED"


def test_idempotency_reserve_replay_and_request_hash_mismatch(tmp_path: Path) -> None:
    _path, uow = _database(tmp_path)
    with uow.begin_immediate() as tx:
        reserved = tx.idempotency.get_or_reserve(
            "operator-a", "approvals/batch", "idem-a", HASH_A, now_ms=10, expires_at_ms=10_000
        )
        assert reserved.kind == "NEW"
        tx.idempotency.save_response(
            "operator-a",
            "approvals/batch",
            "idem-a",
            request_hash=HASH_A,
            response_status=201,
            response_json='{"approved":1}',
        )
        replay = tx.idempotency.get_or_reserve(
            "operator-a", "approvals/batch", "idem-a", HASH_A, now_ms=11, expires_at_ms=10_000
        )
        assert replay.kind == "REPLAY"
        assert replay.response_status == 201
        assert replay.response_json == '{"approved":1}'
        mismatch = tx.idempotency.get_or_reserve(
            "operator-a", "approvals/batch", "idem-a", HASH_B, now_ms=11, expires_at_ms=10_000
        )
        assert mismatch.kind == "MISMATCH"
