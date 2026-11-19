from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from growth_engine.adapters.inbound.cli.main import app
from growth_engine.adapters.outbound.persistence.sqlite.connection import connect
from growth_engine.adapters.outbound.persistence.sqlite.migrator import MigrationRunner
from growth_engine.adapters.outbound.persistence.sqlite.review_store import SqliteReviewStore
from growth_engine.adapters.outbound.persistence.sqlite.uow import SqliteUnitOfWork
from growth_engine.application.dto import EffectiveQcPolicy, QcResult
from growth_engine.application.ops.reprocess_p4_qc_evidence import (
    P4QcEvidenceInsufficient,
    P4QcEvidenceNonFiniteNumber,
    ReprocessP4QcEvidence,
)
from growth_engine.application.review.create_revision import CreateRevision
from growth_engine.domain.delivery.revision import normalize_caption
from tests.growth_engine.support.fakes import FakeClock, SeqIds
from validator_studio.observe_adapter import parse_image_observation_response


CAPTION = "A synthetic lakefront hotel post"
RULESET_HASH = "d" * 64
FACT_HASH = "b" * 64
VARIANT_HASH = "a" * 64


class _OfflineQcEvaluator:
    def __init__(self) -> None:
        self.reprocess_calls = 0
        self.provider_calls = 0

    def compile_policy(self, project: str, subject: str, scenario: str | None) -> EffectiveQcPolicy:
        assert (project, subject, scenario) == ("venho_hotel", "outside", None)
        return EffectiveQcPolicy(project, subject, scenario, RULESET_HASH, ("no visible logo",))

    def reprocess_response(self, variant, caption, facts, policy, response) -> QcResult:
        self.reprocess_calls += 1
        observation = parse_image_observation_response(response)
        assert observation.dna_matches[0].key == "window_frame"
        return QcResult(
            decision="PASS",
            ruleset_hash=policy.ruleset_hash,
            caption_hash=hashlib.sha256(normalize_caption(caption).encode()).hexdigest(),
            fact_snapshot_hash=facts.snapshot_hash,
            result_json=json.dumps({"forbidden_violations": [], "kill_switch_triggered": False}),
        )

    def evaluate(self, *args, **kwargs):  # pragma: no cover - called only on a regression
        self.provider_calls += 1
        raise AssertionError("offline evidence reprocessing must not call a provider")


def _seed_reprocessable_job(database: Path, *, evidence: str | None = None) -> None:
    migrations = Path("growth_engine/adapters/outbound/persistence/sqlite/migrations")
    with connect(database) as connection:
        MigrationRunner(migrations).apply(connection, application_version="p4-qc-reprocess-test")

    caption_hash = hashlib.sha256(normalize_caption(CAPTION).encode()).hexdigest()
    response = {
        "dna_matches": [{"key": "window_frame", "match_state": "MATCH", "confidence": 0.9}],
        "forbidden": [{"rule": "no visible logo", "violated": "false"}],
    }
    events = [
        {"source": "provider", "event": {
            "event": "response_received", "http_status": 200,
            "input_tokens": 1900, "output_tokens": 1102,
        }},
        {"source": "validator", "event": {
            "rawResponse": json.dumps(response), "parseStatus": "raw_captured",
        }},
    ]
    stored_evidence = json.dumps(events, separators=(",", ":")) if evidence is None else evidence
    with connect(database) as connection:
        connection.execute(
            "INSERT INTO runtime_controls(environment,publish_mode,dispatch_epoch,global_pause,policy_version,updated_at) "
            "VALUES ('production','DISABLED','p4-test',1,'v1',1000)"
        )
        connection.execute(
            """INSERT INTO channels(id,project_id,environment,channel_key,platform,remote_account_id,name,
                      enabled,paused,created_at)
               VALUES ('channel-p4','venho_hotel','production','fb_hanoi','facebook',
                       '1124616474074140','Ven Ho Hanoi',1,0,1000)"""
        )
        connection.execute(
            """INSERT INTO channel_configs(id,channel_id,version,make_route_ref,graph_api_version,
                      capability_json,caption_profile,config_hash,created_at)
               VALUES ('config-p4','channel-p4',1,'route-hanoi','v27.0','{}','default',?,1000)""",
            ("c" * 64,),
        )
        connection.execute(
            """INSERT INTO slots(id,project_id,local_date,local_time,timezone,lane,cadence_version,
                      scheduled_at,deadline_at,created_at)
               VALUES ('slot-p4','venho_hotel','2026-11-21','09:00','Asia/Ho_Chi_Minh',
                       'growth','v1',1795226400000,1795230000000,1000)"""
        )
        connection.execute(
            "INSERT INTO slot_targets(id,slot_id,channel_id,required) VALUES ('target-p4','slot-p4','channel-p4',1)"
        )
        connection.execute(
            """INSERT INTO content_packages(id,slot_id,topic_key,pillar,lane,source_snapshot_json,
                      fact_snapshot_json,fact_snapshot_hash,generation_version,created_at)
               VALUES ('package-p4','slot-p4','topic','lake','growth',?,?,?,'v1',1000)""",
            (json.dumps({"captions_by_profile": {"default": CAPTION}}), "{}", FACT_HASH),
        )
        connection.execute(
            """INSERT INTO deliveries(id,target_id,channel_id,package_id,state,created_at,updated_at)
               VALUES ('2509f430-4a4a-47dd-97a9-4b99e8d4ba88','target-p4','channel-p4',
                       'package-p4','DRAFT',1000,1000)"""
        )
        connection.execute(
            """INSERT INTO media_assets(id,source_type,source_ref,source_revision,source_sha256,
                      original_key,metadata_json,created_at)
               VALUES ('asset-p4','library','legacy:test','1',?,'originals/test.jpg','{}',1000)""",
            ("e" * 64,),
        )
        connection.execute(
            """INSERT INTO media_variants(id,asset_id,transform_version,sha256,object_key,width,height,
                      mime,byte_size,qc_status,created_at)
               VALUES ('variant-p4','asset-p4','facebook-v1',?,'variants/test.jpg',1080,1350,
                       'image/jpeg',500,'PENDING',1000)""",
            (VARIANT_HASH,),
        )
        connection.execute(
            """INSERT INTO jobs(id,kind,lane,business_key,payload_json,state,attempts,max_attempts,
                      run_at,last_error,created_at,updated_at)
               VALUES ('e0d00517-3661-4390-a532-6f516e0ef176','assemble_revision','jobs',
                      'assemble:p4','{}','FAILED',1,3,1000,
                      'ERR_GC2_QC_POST_RESPONSE_FAILED: ValueError; filtered response evidence was retained.',1000,1000)"""
        )
        connection.execute(
            "UPDATE jobs SET payload_json=? WHERE id=?",
            (json.dumps({
                "delivery_id": "2509f430-4a4a-47dd-97a9-4b99e8d4ba88",
                "asset_options": [{"asset_id": "asset-p4", "provenance": {"dna_subject": "outside"}}],
                "qc_retry_key": "ea0bb3d3-1a5c-49ef-b60f-840cfca4e319",
            }), "e0d00517-3661-4390-a532-6f516e0ef176"),
        )
        business_key = (
            f"qc:{VARIANT_HASH}:{caption_hash}:{FACT_HASH}:{RULESET_HASH}"
            ":retry:ea0bb3d3-1a5c-49ef-b60f-840cfca4e319"
        )
        connection.execute(
            """INSERT INTO paid_calls(id,business_key,period_key,currency,provider,operation,state,
                      reserved_minor,actual_minor,created_at,settled_at,provider_response_json)
               VALUES ('paid-p4',?,'2026-11','VND','legacy_openai_vision','image_qc','SETTLED',
                       400,400,1000,1001,?)""",
            (business_key, stored_evidence),
        )


def _service(database: Path, qc: _OfflineQcEvaluator) -> ReprocessP4QcEvidence:
    uow_factory = lambda: SqliteUnitOfWork(lambda: connect(database), sleep=lambda _: None)
    clock = FakeClock(2_000_000)
    review_store = SqliteReviewStore(uow_factory, SeqIds("review"), clock)
    create_revision = CreateRevision(review_store, clock, SeqIds("revision"))
    return ReprocessP4QcEvidence(
        uow_factory, qc, create_revision, now_ms=clock.now_ms, id_factory=SeqIds("qc").new_id,
    )


def _cli_env(database: Path, root: Path) -> dict[str, str]:
    return {
        "GE_ENV": "production",
        "GE_DB_PATH": str(database),
        "GE_MEDIA_ROOT": str(root / "media"),
        "GE_PUBLIC_BASE_URL": "https://growth.example.invalid",
        "GE_DASHBOARD_BASE_URL": "https://os.example.invalid",
        "GE_CAPABILITY_KEYS": "synthetic-capability-key",
        "GE_SERVICE_TOKENS": "synthetic-service-token",
        "GE_TELEGRAM_BOT_TOKEN": "synthetic-telegram-token",
        "GE_TELEGRAM_CHAT_ID": "synthetic-chat",
        "GE_MAKE_WEBHOOK_URL_PAGE_A": "https://make.example.invalid/hook",
        "GE_META_READ_TOKEN_FB_HANOI": "synthetic-meta-token",
    }


def test_reprocess_creates_qc_and_in_review_revision_once_without_provider_call(
    tmp_path: Path
) -> None:
    database = tmp_path / "growth.db"
    _seed_reprocessable_job(database)
    qc = _OfflineQcEvaluator()
    service = _service(database, qc)
    job_id = "e0d00517-3661-4390-a532-6f516e0ef176"
    with connect(database) as connection:
        evidence_before = connection.execute(
            "SELECT provider_response_json FROM paid_calls WHERE id='paid-p4'"
        ).fetchone()[0]

    preview = service.preview(job_id)
    assert preview.delivery_id == "2509f430-4a4a-47dd-97a9-4b99e8d4ba88"
    assert preview.evidence_length > 0
    assert "dna_matches" in preview.readable_keys

    runner = CliRunner()
    obj = {"reprocess_p4_qc_evidence_service": service}
    # The line sent to CliRunner is deliberately not trusted as confirmation.
    declined = runner.invoke(app, ["reprocess-p4-qc-evidence", "--job", job_id],
                             env=_cli_env(database, tmp_path), input="REPROCESS\n", obj=obj)
    assert declined.exit_code == 2
    assert "ERR_GC2_OPERATOR_CONFIRMATION_REQUIRED" in declined.output
    with connect(database) as connection:
        assert connection.execute("SELECT count(*) FROM qc_reports").fetchone()[0] == 0
        assert connection.execute("SELECT state FROM deliveries WHERE id=?", (preview.delivery_id,)).fetchone()[0] == "DRAFT"

    preflight = runner.invoke(app, ["reprocess-p4-qc-evidence", "--job", job_id, "--preflight-only"],
                              env=_cli_env(database, tmp_path), obj=obj)
    assert preflight.exit_code == 0 and '"preflight": "READY"' in preflight.output
    with connect(database) as connection:
        assert connection.execute("SELECT count(*) FROM qc_reports").fetchone()[0] == 0

    accepted = runner.invoke(app, ["reprocess-p4-qc-evidence", "--job", job_id, "--operator-confirmed", f"REPROCESS:{job_id}"],
                             env=_cli_env(database, tmp_path), input="not-the-confirmation\n", obj=obj)
    assert accepted.exit_code == 0, accepted.output
    assert '"result": "REPROCESSED"' in accepted.output
    assert '"delivery_state": "IN_REVIEW"' in accepted.output
    replay = runner.invoke(app, ["reprocess-p4-qc-evidence", "--job", job_id, "--preflight-only"],
                           env=_cli_env(database, tmp_path), input="", obj=obj)
    assert replay.exit_code == 0, replay.output
    assert '"result": "ALREADY_PROCESSED"' in replay.output
    status = runner.invoke(app, ["p4-slot-status", "--date", "2026-11-21"], env=_cli_env(database, tmp_path))
    assert status.exit_code == 0, status.output
    job = next(job for job in json.loads(status.output)["jobs"] if job["id"] == job_id)
    assert job["state"] == "FAILED" and job["recovery_status"] == "RECOVERED"
    assert "ValueError" in job["last_error"]
    assert qc.provider_calls == 0 and qc.reprocess_calls >= 2
    with connect(database) as connection:
        assert connection.execute("SELECT count(*) FROM qc_reports").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM delivery_revisions").fetchone()[0] == 1
        assert connection.execute("SELECT state FROM deliveries WHERE id=?", (preview.delivery_id,)).fetchone()[0] == "IN_REVIEW"
        assert connection.execute("SELECT count(*) FROM outbox_commands").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM executions").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM paid_calls").fetchone()[0] == 1
        assert connection.execute("SELECT state FROM paid_calls").fetchone()[0] == "SETTLED"
        evidence_after = connection.execute(
            "SELECT provider_response_json FROM paid_calls WHERE id='paid-p4'"
        ).fetchone()[0]
        assert evidence_after == evidence_before


@pytest.mark.parametrize("confirmation", ["RESOLVE:e0d00517-3661-4390-a532-6f516e0ef176", "REPROCESS:another-job"])
def test_reprocess_refuses_wrong_confirmation(tmp_path: Path, confirmation: str) -> None:
    database = tmp_path / "growth.db"
    _seed_reprocessable_job(database)
    service = _service(database, _OfflineQcEvaluator())
    job_id = "e0d00517-3661-4390-a532-6f516e0ef176"
    result = CliRunner().invoke(
        app,
        ["reprocess-p4-qc-evidence", "--job", job_id, "--operator-confirmed", confirmation],
        env=_cli_env(database, tmp_path),
        input="REPROCESS\n",
        obj={"reprocess_p4_qc_evidence_service": service},
    )
    assert result.exit_code == 2
    assert "ERR_GC2_OPERATOR_CONFIRMATION_REQUIRED" in result.output
    with connect(database) as connection:
        assert connection.execute("SELECT count(*) FROM qc_reports").fetchone()[0] == 0
        assert connection.execute("SELECT state FROM deliveries").fetchone()[0] == "DRAFT"


def test_reprocess_stops_cleanly_when_stored_evidence_is_insufficient(tmp_path: Path) -> None:
    database = tmp_path / "growth.db"
    _seed_reprocessable_job(database, evidence="[]")
    qc = _OfflineQcEvaluator()
    service = _service(database, qc)

    with pytest.raises(P4QcEvidenceInsufficient, match="image observation rawResponse or parsedEvidence"):
        service.preview("e0d00517-3661-4390-a532-6f516e0ef176")
    assert qc.provider_calls == 0 and qc.reprocess_calls == 0
    with connect(database) as connection:
        assert connection.execute("SELECT count(*) FROM qc_reports").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM delivery_revisions").fetchone()[0] == 0
        assert connection.execute("SELECT state FROM deliveries").fetchone()[0] == "DRAFT"
        paid = connection.execute("SELECT state,actual_minor FROM paid_calls").fetchone()
        assert (paid["state"], paid["actual_minor"]) == ("SETTLED", 400)


def test_reprocess_rejects_non_finite_number_with_field_specific_code(tmp_path: Path) -> None:
    database = tmp_path / "growth.db"
    evidence = json.dumps([
        {"source": "provider", "event": {"event": "response_received", "http_status": 200}},
        {"source": "validator", "event": {
            "rawResponse": '{"dna_matches":[{"key":"x","match_state":"match",'
                           '"confidence":NaN}]}',
        }},
    ])
    _seed_reprocessable_job(database, evidence=evidence)
    service = _service(database, _OfflineQcEvaluator())

    with pytest.raises(P4QcEvidenceNonFiniteNumber) as error:
        service.preview("e0d00517-3661-4390-a532-6f516e0ef176")
    assert getattr(error.value, "code", None) == "ERR_GC2_QC_NONFINITE_NUMBER"
    assert "$.dna_matches[0].confidence" in str(error.value)
    with connect(database) as connection:
        assert connection.execute("SELECT count(*) FROM qc_reports").fetchone()[0] == 0
        assert connection.execute("SELECT state FROM deliveries").fetchone()[0] == "DRAFT"


def test_reprocess_rolls_back_every_write_if_revision_fails_mid_transaction(tmp_path: Path) -> None:
    database = tmp_path / "growth.db"
    _seed_reprocessable_job(database)
    service = _service(database, _OfflineQcEvaluator())

    def fail_revision(*_args, **_kwargs):
        raise RuntimeError("synthetic failure after QC report write")

    service._create_revision.execute = fail_revision
    with pytest.raises(RuntimeError, match="synthetic failure"):
        service.execute("e0d00517-3661-4390-a532-6f516e0ef176")

    with connect(database) as connection:
        assert connection.execute("SELECT count(*) FROM qc_reports").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM delivery_revisions").fetchone()[0] == 0
        assert connection.execute("SELECT state FROM deliveries").fetchone()[0] == "DRAFT"
        assert connection.execute("SELECT qc_status FROM media_variants").fetchone()[0] == "PENDING"
        assert connection.execute("SELECT count(*) FROM audit_events WHERE aggregate_id=?",
                                  ("e0d00517-3661-4390-a532-6f516e0ef176",)).fetchone()[0] == 0


def test_status_qc_summary_only_returns_verdict_and_integer_scores() -> None:
    from growth_engine.adapters.inbound.cli.main import _p4_qc_summary

    assert _p4_qc_summary(json.dumps({"validator_report": {
        "verdict": "revise",
        "overall_score_bp": 899900,
        "dna_match_score_bp": "unexpected",
        "notes": ["hidden"],
        "category_scores_bp": {"dna_match": 800000, "unexpected": 1},
        "section_scores": [{"section": "composition", "key": "window_layout", "score_bp": 900000, "reason": "hidden"}],
        "forbidden_violations": [{"confidence_bp": 6999, "rule": "hidden", "violated": False}],
    }})) == {
        "verdict": "revise",
        "overall_score_bp": 899900,
        "category_scores_bp": {"dna_match": 800000},
        "section_scores": [{"section": "composition", "key": "window_layout", "score_bp": 900000}],
        "forbidden_checks": [{"confidence_bp": 6999, "rule_id": "e564b4081d7a9ea4", "violated": False}],
    }


def test_review_caption_preserves_text_and_public_links_without_signed_urls() -> None:
    from growth_engine.adapters.inbound.cli.main import _p4_preview_caption

    caption = "Ven Hồ\nhttps://venhohotel.com/?utm_source=fb\nhttps://example.test/img.jpg?t=secret"
    assert _p4_preview_caption(caption) == (
        "Ven Hồ\nhttps://venhohotel.com/?utm_source=fb\n[URL bảo mật đã ẩn]"
    )
