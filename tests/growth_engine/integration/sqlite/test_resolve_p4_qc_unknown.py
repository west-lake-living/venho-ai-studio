from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from growth_engine.adapters.inbound.cli.main import app
from growth_engine.adapters.outbound.persistence.sqlite.connection import connect
from growth_engine.adapters.outbound.persistence.sqlite.migrator import MigrationRunner
from growth_engine.adapters.outbound.persistence.sqlite.uow import SqliteUnitOfWork
from growth_engine.application.ops.resolve_p4_qc_unknown import ResolveP4QcUnknown


def _seed_unknown_p4_job(database: Path) -> None:
    migrations = Path("growth_engine/adapters/outbound/persistence/sqlite/migrations")
    with connect(database) as connection:
        MigrationRunner(migrations).apply(connection, application_version="resolve-p4-test")
    variant_sha = "a" * 64
    with connect(database) as connection:
        connection.execute(
            """INSERT INTO runtime_controls(environment,publish_mode,dispatch_epoch,global_pause,policy_version,updated_at)
               VALUES ('production','DISABLED','test-epoch',1,'v1',1000000)"""
        )
        connection.execute(
            """INSERT INTO channels(id,project_id,environment,channel_key,platform,remote_account_id,name,enabled,paused,created_at)
               VALUES ('channel-hanoi','venho_hotel','production','fb_hanoi','facebook','1124616474074140','Hanoi',1,0,1)"""
        )
        connection.execute(
            """INSERT INTO slots(id,project_id,local_date,local_time,timezone,lane,cadence_version,scheduled_at,deadline_at,created_at)
               VALUES ('slot-p4','venho_hotel','2026-11-21','09:00','Asia/Ho_Chi_Minh','growth','v1',1000,2000,1)"""
        )
        connection.execute(
            "INSERT INTO slot_targets(id,slot_id,channel_id,required) VALUES ('target-p4','slot-p4','channel-hanoi',1)"
        )
        connection.execute(
            """INSERT INTO content_packages(id,slot_id,topic_key,pillar,lane,source_snapshot_json,fact_snapshot_json,
                      fact_snapshot_hash,generation_version,created_at)
               VALUES ('package-p4','slot-p4','topic','pillar','growth','{}','{}',?,'v1',1)""",
            ("b" * 64,),
        )
        connection.execute(
            """INSERT INTO deliveries(id,target_id,channel_id,package_id,state,created_at,updated_at)
               VALUES ('delivery-p4','target-p4','channel-hanoi','package-p4','DRAFT',1,1000000)"""
        )
        connection.execute(
            """INSERT INTO media_assets(id,source_type,source_ref,source_revision,source_sha256,original_key,metadata_json,created_at)
               VALUES ('asset-p4','library','legacy-local:test','1',?,'originals/test','{}',1)""",
            ("c" * 64,),
        )
        connection.execute(
            """INSERT INTO media_variants(id,asset_id,transform_version,sha256,object_key,width,height,mime,byte_size,qc_status,created_at)
               VALUES ('variant-p4','asset-p4','facebook-v1',?,'variants/test.jpg',100,100,'image/jpeg',100,'PENDING',1)""",
            (variant_sha,),
        )
        connection.execute(
            """INSERT INTO jobs(id,kind,lane,business_key,payload_json,state,attempts,max_attempts,run_at,
                      last_error,created_at,updated_at)
               VALUES ('job-p4','assemble_revision','jobs','assemble:delivery-p4',?,'UNKNOWN',1,3,1000,?,?,?)""",
            (
                json.dumps({"delivery_id": "delivery-p4", "asset_options": [{"asset_id": "asset-p4", "option_id": "C"}]}),
                "ERR_GC2_JOB_QC_PAID_CALL_UNKNOWN: provider may have completed",
                1000000,
                1000000,
            ),
        )
        connection.execute(
            """INSERT INTO paid_calls(id,business_key,period_key,currency,provider,operation,state,reserved_minor,
                      actual_minor,created_at,settled_at)
               VALUES ('paid-p4',?,'2026-11','VND','legacy_openai_vision','image_qc','UNKNOWN',400,NULL,1000000,NULL)""",
            (f"qc:{variant_sha}:{'d' * 64}:{'e' * 64}:{'f' * 64}",),
        )


def test_resolve_p4_qc_unknown_settles_once_audits_and_requeues_once(tmp_path: Path) -> None:
    database = tmp_path / "growth.db"
    _seed_unknown_p4_job(database)
    uow_factory = lambda: SqliteUnitOfWork(lambda: connect(database))
    service = ResolveP4QcUnknown(
        uow_factory,
        now_ms=lambda: 2_000_000,
        id_factory=iter(("qc-retry-1", "audit-event-1")).__next__,
    )

    preview = service.preview("job-p4")
    assert preview.paid_call_state == "UNKNOWN"
    assert preview.actual_minor == 400

    resolved = service.execute("job-p4", input_tokens=1900, output_tokens=1111)
    repeated = service.execute("job-p4", input_tokens=1900, output_tokens=1111)

    assert resolved.already_resolved is False
    assert resolved.qc_retry_key == "qc-retry-1"
    assert repeated.already_resolved is True
    with connect(database) as connection:
        paid = connection.execute("SELECT state,actual_minor,provider_response_json FROM paid_calls WHERE id='paid-p4'").fetchone()
        job = connection.execute("SELECT state,payload_json FROM jobs WHERE id='job-p4'").fetchone()
        audit_count = connection.execute("SELECT count(*) FROM audit_events WHERE action='p4.qc_unknown_resolved_and_requeued'").fetchone()[0]
    assert paid["state"] == "SETTLED" and paid["actual_minor"] == 400
    assert '"input_tokens":1900' in paid["provider_response_json"]
    assert '"output_tokens":1111' in paid["provider_response_json"]
    assert job["state"] == "PENDING"
    assert json.loads(job["payload_json"])["qc_retry_key"] == "qc-retry-1"
    assert audit_count == 1


def test_resolve_cli_requires_exact_confirmation_and_is_idempotent(
    tmp_path: Path
) -> None:
    database = tmp_path / "growth.db"
    _seed_unknown_p4_job(database)
    env = {
        "GE_ENV": "production",
        "GE_DB_PATH": str(database),
        "GE_MEDIA_ROOT": str(tmp_path / "media"),
        "GE_PUBLIC_BASE_URL": "https://growth.example.invalid",
        "GE_DASHBOARD_BASE_URL": "https://os.example.invalid",
        "GE_CAPABILITY_KEYS": "synthetic-capability-key",
        "GE_SERVICE_TOKENS": "synthetic-service-token",
        "GE_TELEGRAM_BOT_TOKEN": "synthetic-telegram-token",
        "GE_TELEGRAM_CHAT_ID": "synthetic-chat",
        "GE_MAKE_WEBHOOK_URL_PAGE_A": "https://make.example.invalid/hook",
        "GE_META_READ_TOKEN_FB_HANOI": "synthetic-meta-token",
    }
    args = [
        "resolve-p4-qc-unknown", "--job", "job-p4", "--actual-minor", "400",
        "--input-tokens", "1900", "--output-tokens", "1111",
    ]
    runner = CliRunner()
    service = ResolveP4QcUnknown(
        lambda: SqliteUnitOfWork(lambda: connect(database)),
        now_ms=lambda: 2_000_000,
    )
    obj = {"resolve_p4_qc_unknown_service": service}
    declined = runner.invoke(app, args, env=env, input="resolve\n", obj=obj)
    assert declined.exit_code == 2, declined.output
    assert "ERR_GC2_OPERATOR_CONFIRMATION_REQUIRED" in declined.output
    with connect(database) as connection:
        assert connection.execute("SELECT state FROM paid_calls WHERE id='paid-p4'").fetchone()[0] == "UNKNOWN"
        assert connection.execute("SELECT state FROM jobs WHERE id='job-p4'").fetchone()[0] == "UNKNOWN"

    for wrong in ("REPROCESS:job-p4", "RESOLVE:another-job"):
        blocked = runner.invoke(app, [*args, "--operator-confirmed", wrong], env=env, obj=obj)
        assert blocked.exit_code == 2 and "ERR_GC2_OPERATOR_CONFIRMATION_REQUIRED" in blocked.output
    preflight = runner.invoke(app, [*args, "--preflight-only"], env=env, obj=obj)
    assert preflight.exit_code == 0 and '"preflight": "READY"' in preflight.output
    with connect(database) as connection:
        assert connection.execute("SELECT state FROM paid_calls WHERE id='paid-p4'").fetchone()[0] == "UNKNOWN"

    accepted = runner.invoke(app, [*args, "--operator-confirmed", "RESOLVE:job-p4"], env=env, input="not-a-confirmation\n", obj=obj)
    assert accepted.exit_code == 0, accepted.output
    assert "RESOLVED_AND_REQUEUED" in accepted.output
    replay = runner.invoke(app, [*args, "--preflight-only"], env=env, input="", obj=obj)
    assert replay.exit_code == 0, replay.output
    assert "ALREADY_RESOLVED" in replay.output
    assert "RESOLVED_AND_REQUEUED" not in replay.output
