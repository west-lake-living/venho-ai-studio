from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from io import BytesIO
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from growth_engine.application.content.generate_package import GeneratePackageCommand
from growth_engine.application.dto import DraftPackage, EffectiveQcPolicy, FactSnapshot, QcResult
from growth_engine.application.review.approve_group import ApprovalItem
from growth_engine.domain.kernel.hashing import sha256_hex
from growth_engine.domain.publishing.runtime_mode import PublishMode
from growth_engine.settings import Settings
from tests.growth_engine.support.fakes import FakeClock, SeqIds
from tests.growth_engine.test_manage_production_channels import _controls, _manifest, channels


class _FakeContentGenerator:
    def __init__(self, image_path: Path) -> None:
        self.image_path = image_path
        self.image_provider = SimpleNamespace(enabled=True)
        self.image_alternatives_enabled = False

    def draft(self, request) -> DraftPackage:
        return DraftPackage(
            topic_key="p4-test-topic",
            pillar="west_lake_life",
            brief="Synthetic P4 content brief.",
            fact_keys=(),
            captions_by_profile={"default": "Synthetic P4 caption."},
            image_options=({
                "option_id": "A",
                "path": str(self.image_path),
                "provenance": {"dna_subject": "outside", "_synthetic": True},
            },),
        )


class _TextOnlyFakeGenerator:
    def __init__(self) -> None:
        self.image_provider = SimpleNamespace(enabled=False)
        self.image_alternatives_enabled = False
        self.calls = 0

    def draft(self, request) -> DraftPackage:
        self.calls += 1
        return DraftPackage(
            topic_key="p4-test-topic-without-media",
            pillar="west_lake_life",
            brief="Synthetic P4 content brief.",
            fact_keys=(),
            captions_by_profile={"default": "Ảnh chụp thật tại Ven Hồ Hotel."},
            image_options=(),
        )


class _FakeFacts:
    def approved_facts(self, keys, at_ms):
        return FactSnapshot({}, sha256_hex(b"{}"))


class _FakeQcEvaluator:
    def compile_policy(self, project, subject, scenario):
        return EffectiveQcPolicy(project, subject, scenario, "a" * 64, ())

    def evaluate(self, variant, caption, facts, policy):
        return QcResult(
            decision="PASS",
            ruleset_hash=policy.ruleset_hash,
            caption_hash=hashlib.sha256(caption.encode("utf-8")).hexdigest(),
            fact_snapshot_hash=facts.snapshot_hash,
            result_json='{"_synthetic":true}',
        )


class _FakeMake:
    def __init__(self) -> None:
        self.calls = 0

    def deliver(self, route_ref, envelope):
        self.calls += 1
        raise AssertionError("FakeMake must not receive a P4 preparation delivery")


def test_production_p4_fake_e2e_approves_without_dispatch_while_disabled(
    tmp_path: Path, monkeypatch
) -> None:
    image_path = tmp_path / "synthetic-source.png"
    Image.new("RGB", (800, 1000), (42, 96, 120)).save(image_path, format="PNG")
    clock = FakeClock(int(datetime(2026, 11, 10, 2, 0, tzinfo=timezone.utc).timestamp() * 1000))
    settings = Settings(
        env="production",
        db_path=str(tmp_path / "growth_engine.db"),
        media_root=str(tmp_path / "media"),
        public_base_url="https://growth.example.invalid",
        dashboard_base_url="https://os.example.invalid",
        capability_keys="synthetic:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        service_tokens="synthetic:hash",
        make_webhook_urls={"PAGE_A": "https://make.example.invalid/fake"},
        meta_read_tokens={"fb_hanoi": "synthetic-read-token"},
        telegram={"BOT_TOKEN": "synthetic-bot", "CHAT_ID": "synthetic-chat"},
    )
    from growth_engine.bootstrap import build_container

    container = build_container(settings, clock=clock, ids=SeqIds("p4-e2e"))
    container.migration_service.run(Path(settings.db_path), check=False)
    channels.provision(settings.db_path, _manifest(), now_ms=clock.now_ms())
    _controls(Path(settings.db_path), "DISABLED")
    channels.set_enabled(
        settings.db_path,
        "fb_hanoi",
        True,
        prepare_only=True,
        now_ms=clock.now_ms(),
    )

    monkeypatch.setenv("ANTHROPIC_API_KEY", "synthetic-anthropic-secret")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-openai-secret")
    with container.uow_factory().read_only() as tx:
        provider_check = container.doctor_service._p4_provider_budget_check(tx.connection)
    assert provider_check.status == "PASS"
    assert "ANTHROPIC_API_KEY" in provider_check.detail
    assert "OPENAI_API_KEY" in provider_check.detail
    assert "synthetic-anthropic-secret" not in provider_check.detail
    assert "synthetic-openai-secret" not in provider_check.detail
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    with container.uow_factory().read_only() as tx:
        missing_key_check = container.doctor_service._p4_provider_budget_check(tx.connection)
    assert missing_key_check.status == "FAIL"
    assert "ANTHROPIC_API_KEY" in missing_key_check.detail
    assert "synthetic-openai-secret" not in missing_key_check.detail

    container.generate_package._generator = _FakeContentGenerator(image_path)
    container.generate_package._fact_source = _FakeFacts()
    container.evaluate_qc._evaluator = _FakeQcEvaluator()
    queued = container.queue_slot_generation.execute(date(2026, 11, 13))
    assert queued.state == "PENDING"

    jobs = container.content_jobs_worker.process_once(limit=20)
    assert jobs.claimed == 3
    if jobs.completed != 3:
        with container.uow_factory().read_only() as tx:
            detail = [dict(row) for row in tx.connection.execute(
                "SELECT kind, state, last_error FROM jobs ORDER BY created_at, kind"
            ).fetchall()]
        raise AssertionError(f"expected all three content jobs to complete; got {jobs!r}, {detail!r}")
    assert jobs.failed == 0
    assert jobs.unknown == 0

    with container.uow_factory().read_only() as tx:
        delivery = tx.connection.execute(
            """SELECT d.id, d.state, d.row_version, d.current_revision_id,
                      r.payload_hash, r.variant_id, r.qc_report_id,
                      v.mime, v.qc_status, q.decision
               FROM deliveries d
               JOIN delivery_revisions r ON r.id=d.current_revision_id
               JOIN media_variants v ON v.id=r.variant_id
               JOIN qc_reports q ON q.id=r.qc_report_id
               JOIN channels c ON c.id=d.channel_id
               WHERE c.channel_key='fb_hanoi'"""
        ).fetchone()
        paid_rows = tx.connection.execute(
            "SELECT operation, state, actual_minor FROM paid_calls ORDER BY operation"
        ).fetchall()
        controls = tx.controls.get("production")
    assert delivery["state"] == "IN_REVIEW"
    assert delivery["mime"] == "image/jpeg"
    assert delivery["qc_status"] == "PASS"
    assert delivery["decision"] == "PASS"
    assert [(row["operation"], row["state"]) for row in paid_rows] == [
        ("draft_package", "SETTLED"),
        ("image_qc", "SETTLED"),
    ]
    assert controls is not None and controls.mode is PublishMode.DISABLED and controls.global_pause

    approved = container.approve_group.execute(
        (
            ApprovalItem(
                delivery_id=str(delivery["id"]),
                revision_id=str(delivery["current_revision_id"]),
                payload_hash=str(delivery["payload_hash"]),
                expected_row_version=int(delivery["row_version"]),
            ),
        ),
        actor="operator-test",
        principal="operator-test",
        idempotency_key="p4-production-e2e-approval",
    )
    assert len(approved.approvals) == 1

    with container.uow_factory().read_only() as tx:
        scheduled_at = int(tx.connection.execute(
            """SELECT s.scheduled_at FROM slots s
               JOIN slot_targets st ON st.slot_id=s.id
               JOIN deliveries d ON d.target_id=st.id
               WHERE d.id=?""",
            (delivery["id"],),
        ).fetchone()[0])
    clock.set(scheduled_at + 60_000)
    make = _FakeMake()
    container.dispatch_outbox._transport = make
    enqueue = container.enqueue_due.execute(clock.now_ms())
    dispatch = container.dispatch_outbox.execute(clock.now_ms())

    assert enqueue.skipped_reason == "MODE_NOT_LIVE_MANUAL"
    assert dispatch.claimed_count == 0
    assert make.calls == 0
    with container.uow_factory().begin_immediate() as tx:
        tx.connection.execute(
            "UPDATE jobs SET state='FAILED', last_error='historical QC error' "
            "WHERE kind='assemble_revision' AND json_extract(payload_json,'$.delivery_id')=?",
            (delivery["id"],),
        )
    readiness = container.cutover_readiness.execute("2026-11-13", "09:00")
    assert readiness.ready is True
    assert readiness.mapping_dry_run == "PASS"
    assert readiness.mapping_target_id == "1124616474074140"
    assert readiness.mapping_route_ref == "GE_MAKE_WEBHOOK_URL_PAGE_A"
    with container.uow_factory().read_only() as tx:
        state = tx.connection.execute(
            "SELECT state FROM deliveries WHERE id=?", (delivery["id"],)
        ).fetchone()[0]
        command_count = tx.connection.execute(
            "SELECT count(*) FROM outbox_commands WHERE delivery_id=?", (delivery["id"],)
        ).fetchone()[0]
        execution_count = tx.connection.execute(
            "SELECT count(*) FROM executions WHERE delivery_id=?", (delivery["id"],)
        ).fetchone()[0]
    assert state == "APPROVED"
    assert command_count == 0
    assert execution_count == 0

    with container.uow_factory().read_only() as tx:
        deadline_at = tx.connection.execute(
            "SELECT deadline_at FROM delivery_revisions WHERE delivery_id=?", (delivery["id"],)
        ).fetchone()[0]
    clock.set(deadline_at)
    assert container.cutover_readiness.execute("2026-11-13", "09:00").ready
    clock.set(deadline_at + 1)
    overdue = container.cutover_readiness.execute("2026-11-13", "09:00")
    assert not overdue.ready
    assert "target_delivery_past_publish_deadline" in overdue.reasons
    assert [(item.delivery_id, item.state) for item in overdue.overdue_deliveries] == [
        (delivery["id"], "APPROVED"),
    ]
    assert container.expire_overdue.execute(clock.now_ms()).expired_delivery_ids == (delivery["id"],)
    assert not container.cutover_readiness.execute("2026-11-13", "09:00").overdue_deliveries

    connection = sqlite3.connect(settings.db_path)
    connection.execute("DROP TRIGGER no_channel_config_update")
    connection.execute(
        "UPDATE channel_configs SET make_route_ref='GE_MAKE_WEBHOOK_URL_PAGE_B' "
        "WHERE channel_id=(SELECT id FROM channels WHERE channel_key='fb_hanoi')"
    )
    connection.commit()
    connection.close()
    mismatched_mapping = container.cutover_readiness.execute("2026-11-13", "09:00")
    assert mismatched_mapping.ready is False
    assert mismatched_mapping.mapping_dry_run == "FAIL"
    assert "slot_mapping_mismatch" in mismatched_mapping.reasons


def test_p4_repairs_text_only_draft_from_allowlisted_legacy_local_photo_without_regeneration(
    tmp_path: Path, monkeypatch, caplog
) -> None:
    import pillow_heif

    photo_buffer = BytesIO()
    pillow_heif.from_pillow(Image.new("RGB", (900, 1200), (43, 91, 117))).save(photo_buffer)
    photo_bytes = photo_buffer.getvalue()
    photo_sha = hashlib.sha256(photo_bytes).hexdigest()
    legacy_root = tmp_path / "growth-runtime/venho-ai-studio/assets/raw"
    photo_path = legacy_root / "outside" / "approved-rooftop-photo.jpeg"
    photo_path.parent.mkdir(parents=True)
    photo_path.write_bytes(photo_bytes)
    image_config = tmp_path / "growth-engine-image-library.yaml"
    image_config.write_text(
        "version: 1\nsource: local_legacy_library\nallowlist:\n"
        "  venho_rooftop_railing_approved:\n"
        f"    - path: outside/{photo_path.name}\n      sha256: {photo_sha}\n",
        encoding="utf-8",
    )
    clock = FakeClock(int(datetime(2026, 11, 10, 2, 0, tzinfo=timezone.utc).timestamp() * 1000))
    settings = Settings(
        env="production",
        db_path=str(tmp_path / "growth_engine.db"),
        media_root=str(tmp_path / "media"),
        public_base_url="https://growth.example.invalid",
        dashboard_base_url="https://os.example.invalid",
        image_library_config=str(image_config),
        legacy_assets_root=str(legacy_root),
        capability_keys="synthetic:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        service_tokens="synthetic:hash",
        make_webhook_urls={"PAGE_A": "https://make.example.invalid/fake"},
        meta_read_tokens={"fb_hanoi": "synthetic-read-token"},
        telegram={"BOT_TOKEN": "synthetic-bot", "CHAT_ID": "synthetic-chat"},
    )
    from growth_engine.bootstrap import build_container

    container = build_container(settings, clock=clock, ids=SeqIds("p4-repair"))
    container.migration_service.run(Path(settings.db_path), check=False)
    channels.provision(settings.db_path, _manifest(), now_ms=clock.now_ms())
    _controls(Path(settings.db_path), "DISABLED")
    channels.set_enabled(
        settings.db_path, "fb_hanoi", True, prepare_only=True, now_ms=clock.now_ms()
    )
    text_generator = _TextOnlyFakeGenerator()
    container.generate_package._generator = text_generator
    container.generate_package._fact_source = _FakeFacts()
    container.evaluate_qc._evaluator = _FakeQcEvaluator()

    with caplog.at_level(logging.INFO):
        queued = container.queue_slot_generation.execute(date(2026, 11, 21), channel_key="fb_hanoi")
        assert queued.state == "PENDING"
        generated = container.content_jobs_worker.process_once(limit=20)
    assert generated.claimed == generated.completed == 1
    assert generated.failed == 0
    assert text_generator.calls == 1
    completion = [record.message for record in caplog.records if "content job finished" in record.message]
    assert len(completion) == 1 and "state=SUCCEEDED" in completion[0]

    with container.uow_factory().read_only() as tx:
        delivery = tx.connection.execute(
            """SELECT d.id, d.package_id, d.state, d.current_revision_id
               FROM deliveries d JOIN channels c ON c.id=d.channel_id
               JOIN slots s ON s.id=(SELECT slot_id FROM slot_targets WHERE id=d.target_id)
               WHERE c.channel_key='fb_hanoi' AND s.local_date='2026-11-21'"""
        ).fetchone()
        package_before = str(delivery["package_id"])
        assert json.loads(tx.connection.execute(
            "SELECT source_snapshot_json FROM content_packages WHERE id=?", (package_before,)
        ).fetchone()[0])["images"] == []
        assert tx.connection.execute(
            "SELECT count(*) FROM jobs WHERE kind='assemble_revision' AND payload_json LIKE ?",
            (f"%{delivery['id']}%",),
        ).fetchone()[0] == 0
    assert delivery["state"] == "DRAFT"
    assert delivery["current_revision_id"] is None

    preview = container.repair_slot_media.preview_context(
        date(2026, 11, 21), channel_key="fb_hanoi"
    )
    assert preview["delivery_id"] == str(delivery["id"])
    assert preview["topic_key"] == "p4-test-topic-without-media"

    repair = container.repair_slot_media.execute(
        date(2026, 11, 21),
        channel_key="fb_hanoi",
        reference_asset_id="venho_rooftop_railing_approved",
    )
    assert repair.delivery_id == str(delivery["id"])
    assert repair.source_sha256 == photo_sha
    assert repair.source_relative_path == "outside/approved-rooftop-photo.jpeg"

    # Simulate the original assembly job being picked before its variant exists.
    connection = sqlite3.connect(settings.db_path)
    connection.execute("DELETE FROM jobs WHERE kind='prepare_variant' AND payload_json LIKE ?", (f"%{repair.asset_id}%",))
    connection.commit()
    connection.close()
    with caplog.at_level(logging.INFO):
        blocked = container.content_jobs_worker.process_once(limit=20)
    assert blocked.claimed == 0
    assert blocked.deferred == 0
    assert blocked.failed == 0
    assert any("content job waiting" in record.message for record in caplog.records)
    with container.uow_factory().read_only() as tx:
        assembly = tx.connection.execute(
            "SELECT state,attempts,last_error FROM jobs WHERE id=?", (repair.assemble_job_id,)
        ).fetchone()
    assert assembly["state"] == "PENDING"
    assert assembly["attempts"] == 0
    assert assembly["last_error"].startswith("ERR_GC2_MEDIA_VARIANT_PENDING:")

    # Re-running the audited repair requeues only missing media work; package/provider are untouched.
    repair_again = container.repair_slot_media.execute(
        date(2026, 11, 21),
        channel_key="fb_hanoi",
        reference_asset_id="venho_rooftop_railing_approved",
    )
    assert repair_again.asset_id == repair.asset_id
    assert repair_again.assemble_job_id == repair.assemble_job_id
    finished = container.content_jobs_worker.process_once(limit=20)
    assert finished.claimed == finished.completed == 2
    assert finished.failed == 0
    assert text_generator.calls == 1

    with container.uow_factory().read_only() as tx:
        stored_asset = tx.media.get_asset(repair.asset_id)
        final_delivery = tx.connection.execute(
            "SELECT state,current_revision_id FROM deliveries WHERE id=?", (repair.delivery_id,)
        ).fetchone()
        package_count = int(tx.connection.execute(
            "SELECT count(*) FROM content_packages WHERE id=?", (package_before,)
        ).fetchone()[0])
        draft_calls = int(tx.connection.execute(
            "SELECT count(*) FROM paid_calls WHERE operation='draft_package' AND state='SETTLED'"
        ).fetchone()[0])
        variant = tx.connection.execute(
            """SELECT v.mime,v.qc_status,q.decision
               FROM delivery_revisions r JOIN media_variants v ON v.id=r.variant_id
               JOIN qc_reports q ON q.id=r.qc_report_id WHERE r.id=?""",
            (final_delivery["current_revision_id"],),
        ).fetchone()
        controls = tx.controls.get("production")
        command_count = tx.connection.execute(
            "SELECT count(*) FROM outbox_commands WHERE delivery_id=?", (repair.delivery_id,)
        ).fetchone()[0]
        execution_count = tx.connection.execute(
            "SELECT count(*) FROM executions WHERE delivery_id=?", (repair.delivery_id,)
        ).fetchone()[0]
    assert stored_asset is not None and stored_asset.source_sha256 == photo_sha
    assert package_count == 1 and draft_calls == 1
    assert final_delivery["state"] == "IN_REVIEW"
    assert variant["mime"] == "image/jpeg" and variant["qc_status"] == variant["decision"] == "PASS"
    assert controls.mode is PublishMode.DISABLED and controls.global_pause
    assert command_count == execution_count == 0

    from typer.testing import CliRunner
    from growth_engine.adapters.inbound.cli.main import app as engine_cli

    connection = sqlite3.connect(settings.db_path)
    connection.execute(
        """INSERT INTO paid_calls
           (id,business_key,period_key,currency,provider,operation,state,
            reserved_minor,actual_minor,external_job_id,created_at,settled_at)
           VALUES ('unrelated-call','generate:another-slot:spec:version','2026-11','VND',
                   'fake','unrelated','SETTLED',1,1,NULL,9999999999999,9999999999999)"""
    )
    connection.commit()
    connection.close()

    cli_env = {
        "GE_ENV": "production",
        "GE_DB_PATH": settings.db_path,
        "GE_MEDIA_ROOT": settings.media_root,
        "GE_PUBLIC_BASE_URL": settings.public_base_url,
        "GE_DASHBOARD_BASE_URL": settings.dashboard_base_url,
        "GE_CAPABILITY_KEYS": "synthetic-capability-secret",
        "GE_SERVICE_TOKENS": "synthetic-service-secret",
        "GE_TELEGRAM_BOT_TOKEN": "synthetic-telegram-secret",
        "GE_TELEGRAM_CHAT_ID": "synthetic-chat-id",
        "GE_MAKE_WEBHOOK_URL_PAGE_A": "https://make.example.invalid/synthetic-secret",
        "GE_META_READ_TOKEN_FB_HANOI": "synthetic-meta-secret",
    }
    status = CliRunner().invoke(engine_cli, ["p4-slot-status", "--date", "2026-11-21"], env=cli_env)
    preview = CliRunner().invoke(engine_cli, ["p4-review-preview", "--delivery", repair.delivery_id], env=cli_env)
    assert preview.exit_code == 0, preview.output
    review = json.loads(preview.output)
    assert review["page_id"] == "1124616474074140"
    assert review["scheduled_at_ict"] == "2026-11-21T09:00:00+07:00"
    assert review["mime"] == "image/jpeg"
    assert review["sha256"] in review["variant_path"]
    assert review["caption"]
    assert status.exit_code == 0, status.output
    status_json = json.loads(status.stdout)
    assert status_json["delivery"]["state"] == "IN_REVIEW"
    assert status_json["revision"]["mime"] == "image/jpeg"
    assert status_json["revision"]["qc_decision"] == "PASS"
    assert status_json["controls"] == {"publish_mode": "DISABLED", "global_pause": 1}
    assert status_json["outbox_count"] == status_json["execution_count"] == 0
    assert {row["operation"] for row in status_json["paid_calls"]} == {"draft_package", "image_qc"}
    assert all(secret not in status.stdout for secret in (
        "synthetic-capability-secret", "synthetic-service-secret", "synthetic-telegram-secret",
        "synthetic-chat-id", "synthetic-meta-secret", "synthetic-secret",
    ))


def test_paused_live_rollout_prepares_three_targets_and_stays_paused(tmp_path, monkeypatch):
    from growth_engine.adapters.inbound.cli import cutover_ops
    from growth_engine.bootstrap import build_container

    image = tmp_path / "rooftop.png"
    Image.new("RGB", (800, 1000), (42, 96, 120)).save(image)
    clock = FakeClock(int(datetime(2026, 11, 27, 3, tzinfo=timezone.utc).timestamp() * 1000))
    hook = "https://make.example.invalid/mock"
    settings = Settings(
        env="production", db_path=str(tmp_path / "growth.db"), media_root=str(tmp_path / "media"),
        make_webhook_urls={"PAGE_A": hook, "PAGE_B": hook, "IG_VENHO": hook},
        public_base_url="https://growth.example.invalid",
        capability_keys="synthetic:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    )
    container = build_container(settings, clock=clock, ids=SeqIds("p4-group"))
    container.migration_service.run(Path(settings.db_path), check=False)
    channels.provision(settings.db_path, _manifest(), now_ms=clock.now_ms())
    _controls(Path(settings.db_path), "LIVE_MANUAL")
    for key in ("fb_hanoi", "fb_venho", "ig_venho"):
        channels.set_enabled(settings.db_path, key, True, now_ms=clock.now_ms())
    container.generate_package._generator = _FakeContentGenerator(image)
    container.generate_package._fact_source = _FakeFacts()
    container.evaluate_qc._evaluator = _FakeQcEvaluator()

    queued = container.queue_slot_generation.execute(date(2026, 11, 28), channel_key="group")
    assert not queued.replayed
    assert container.queue_slot_generation.execute(date(2026, 11, 28), channel_key="group").replayed
    jobs = container.content_jobs_worker.process_once(limit=20)
    assert jobs.failed == jobs.unknown == 0
    monkeypatch.setattr(cutover_ops, "now_ms", clock.now_ms)
    monkeypatch.setattr("growth_engine.application.ops.cutover_readiness.time.time_ns", lambda: clock.now_ms() * 1_000_000)
    cutover_ops.backup(settings)
    assert cutover_ops.rehearsal(settings)["result"] == "PASS"
    stage = cutover_ops.pending_gate(settings, "2026-11-28", channels=set(cutover_ops.TARGETS))
    assert stage["result"] == "PASS", stage
    assert stage["controls"]["global_pause"] == 1
    assert {row["state"] for row in stage["deliveries"]} == {"IN_REVIEW"}
    assert len(stage["deliveries"]) == 3
    assert all(not row["commands"] and not row["executions"] for row in stage["deliveries"])
    approved = cutover_ops.pending_gate(settings, "2026-11-28", approved=True, channels=set(cutover_ops.TARGETS))
    assert "slot_targets_not_approved" in approved["reasons"]
    with container.uow_factory().read_only() as tx:
        assert tx.connection.execute("SELECT count(DISTINCT package_id) FROM deliveries").fetchone()[0] == 1


def _generation_recovery_fixture(tmp_path):
    from growth_engine.bootstrap import build_container

    clock = FakeClock(int(datetime(2026, 11, 24, 11, tzinfo=timezone.utc).timestamp() * 1000))
    settings = Settings(
        env="production", db_path=str(tmp_path / "growth.db"), media_root=str(tmp_path / "media"),
        public_base_url="https://growth.example.invalid",
        make_webhook_urls={key: "https://make.example.invalid/fake" for key in ("PAGE_A", "PAGE_B", "IG_VENHO")},
    )
    container = build_container(settings, clock=clock, ids=SeqIds("generation"))
    container.migration_service.run(Path(settings.db_path), check=False)
    channels.provision(settings.db_path, _manifest(), now_ms=clock.now_ms())
    _controls(Path(settings.db_path), "DISABLED")
    channels.set_enabled(settings.db_path, "fb_hanoi", True, prepare_only=True, now_ms=clock.now_ms())
    image = tmp_path / "source.jpg"
    Image.new("RGB", (800, 1000), (42, 96, 120)).save(image)
    container.generate_package._fact_source = _FakeFacts()
    return settings, container, clock, image


class _SharedLibraryGenerator:
    image_provider = None

    def __init__(self, image):
        self.calls = 0
        self.image = image

    def draft(self, request):
        self.calls += 1
        return DraftPackage(
            "west-lake", "hotel", "test brief", (), {"default": "caption"},
            ({"option_id": "C", "path": str(self.image),
              "provenance": {"source_ref": "legacy-local:westlake/same.jpg", "token": "fake-secret"}},),
        )


def test_second_slot_reuses_library_asset_and_variant_job(tmp_path):
    from dataclasses import replace

    import pytest

    _, container, _, image = _generation_recovery_fixture(tmp_path)
    generator = _SharedLibraryGenerator(image)
    container.generate_package._generator = generator
    container.evaluate_qc._evaluator = _FakeQcEvaluator()
    container.queue_slot_generation.execute(date(2026, 11, 25))
    assert container.content_jobs_worker.process_once().completed == 3
    with container.uow_factory().begin_immediate() as tx:
        asset_id = tx.connection.execute("SELECT id FROM media_assets").fetchone()[0]
        asset = tx.media.get_asset(asset_id)
        # Reproduce the exact constraint raised by pre-fix ingest.
        with pytest.raises(sqlite3.IntegrityError, match=r"UNIQUE constraint failed: media_assets.source_type, media_assets.source_ref, media_assets.source_revision"):
            tx.media.save_asset(replace(asset, id="another-asset-id"))
        prepare_id = tx.connection.execute("SELECT id FROM jobs WHERE kind='prepare_variant'").fetchone()[0]
        prepare_job = tx.jobs.get(prepare_id)
        with pytest.raises(sqlite3.IntegrityError, match=r"UNIQUE constraint failed: jobs.kind, jobs.business_key"):
            tx.jobs.save(replace(prepare_job, id="another-prepare-id"))
    container.queue_slot_generation.execute(date(2026, 11, 27))
    result = container.content_jobs_worker.process_once()
    assert result.completed == 2 and result.failed == result.unknown == 0
    with container.uow_factory().read_only() as tx:
        packages = tx.connection.execute("SELECT source_snapshot_json FROM content_packages").fetchall()
        assert len(packages) == 2
        assert {json.loads(row[0])["images"][0]["asset_id"] for row in packages} == {asset_id}
        assert tx.connection.execute("SELECT count(*) FROM jobs WHERE kind='prepare_variant'").fetchone()[0] == 1
        assert tx.connection.execute("SELECT count(*) FROM media_variants").fetchone()[0] == 1
    assert generator.calls == 2


def test_generation_reprocess_rolls_back_and_never_calls_provider(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from growth_engine.adapters.inbound.cli.main import app

    settings, container, clock, image = _generation_recovery_fixture(tmp_path)
    generator = _SharedLibraryGenerator(image)
    container.generate_package._generator = generator
    container.queue_slot_generation.execute(date(2026, 11, 27))
    with container.uow_factory().begin_immediate() as tx:
        tx.connection.execute(
            "CREATE TRIGGER fail_package BEFORE INSERT ON content_packages BEGIN SELECT RAISE(ABORT,'hidden'); END"
        )
    result = container.content_jobs_worker.process_once()
    assert result.failed == 1 and result.unknown == 0
    with container.uow_factory().begin_immediate() as tx:
        paid = tx.connection.execute("SELECT * FROM paid_calls").fetchone()
        outer = tx.connection.execute("SELECT * FROM jobs WHERE kind='generate_slot'").fetchone()
        assert paid["state"] == "SETTLED" and paid["actual_minor"] == paid["reserved_minor"]
        assert json.loads(paid["provider_response_json"])["assets"]
        assert "fake-secret" not in paid["provider_response_json"]
        assert str(image) not in paid["provider_response_json"]
        assert "ERR_GC2_GENERATION_POST_RESPONSE_FAILED: complete_generation: SQLITE_CONSTRAINT_TRIGGER" in outer["last_error"]
        assert tx.connection.execute("SELECT count(*) FROM media_assets").fetchone()[0] == 0
        tx.connection.execute("DROP TRIGGER fail_package")
        tx.connection.execute(
            """CREATE TRIGGER fail_recovery_audit BEFORE INSERT ON audit_events
               WHEN NEW.action='generation.evidence_reprocessed' BEGIN SELECT RAISE(ABORT,'hidden'); END"""
        )

    monkeypatch.setattr(Settings, "from_env", classmethod(lambda cls: settings))
    monkeypatch.setattr("growth_engine.adapters.inbound.cli.main.time.time_ns", lambda: clock.now_ms() * 1_000_000)
    runner = CliRunner()
    base = ["reprocess-generation-evidence", "--job", outer["id"]]

    def invoke(*args):
        return runner.invoke(app, [*base, *args], obj={"container": container})

    assert invoke().exit_code == 2
    preview = invoke("--preflight-only")
    assert preview.exit_code == 0, (preview.output, preview.exception)
    confirmation = ("--operator-confirmed", f"REPROCESS:{outer['id']}")
    assert invoke(*confirmation).exit_code == 1
    with container.uow_factory().begin_immediate() as tx:
        for table in ("media_assets", "deliveries", "content_packages"):
            assert tx.connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0
        assert tx.connection.execute("SELECT state FROM jobs WHERE kind='generate_slot'").fetchone()[0] == "FAILED"
        tx.connection.execute("DROP TRIGGER fail_recovery_audit")
    done = invoke(*confirmation)
    assert done.exit_code == 0, done.output
    assert "REPROCESSED" in done.output
    assert "ALREADY_PROCESSED" in invoke(*confirmation).output
    with container.uow_factory().read_only() as tx:
        assert tx.connection.execute("SELECT count(*) FROM paid_calls").fetchone()[0] == 1
        assert tx.connection.execute("SELECT count(*) FROM deliveries").fetchone()[0] == 1
        assert tx.connection.execute("SELECT state FROM jobs WHERE kind='generate_slot'").fetchone()[0] == "SUCCEEDED"
    assert generator.calls == 1


def test_generation_unknown_resolution_is_atomic_and_clears_t2(tmp_path, monkeypatch):
    import pytest

    from growth_engine.adapters.inbound.cli import cutover_ops

    settings, container, clock, _ = _generation_recovery_fixture(tmp_path)
    monkeypatch.setattr(cutover_ops, "fresh_backup", lambda _: None)

    class Timeout:
        image_provider = None

        def draft(self, request):
            raise TimeoutError("no response")

    container.generate_package._generator = Timeout()
    container.queue_slot_generation.execute(date(2026, 11, 25))
    assert container.content_jobs_worker.process_once().unknown == 1
    assert cutover_ops.generation_clear(settings) == {"result": "FAIL", "open_generation_unknown": 1}
    readiness_before = container.cutover_readiness.execute("2026-11-27").reasons
    gates_before = [
        cutover_ops.pending_gate(settings, "2026-11-27", **options)["reasons"]
        for options in ({"require_disabled": True}, {"approved": True})
    ]
    with container.uow_factory().begin_immediate() as tx:
        job_id = tx.connection.execute("SELECT id FROM jobs WHERE kind='generate_slot'").fetchone()[0]
        tx.connection.execute(
            """CREATE TRIGGER fail_resolution BEFORE INSERT ON audit_events
               WHEN NEW.action='generation.unknown_resolved' BEGIN SELECT RAISE(ABORT,'hidden'); END"""
        )

    store = container.generation_store
    inputs = {"action": "RESOLVE", "now_ms": clock.now_ms(), "actual_minor": 6200}
    assert store.operator_job(job_id, **inputs)[0]["preflight"] == "READY"
    with pytest.raises(sqlite3.IntegrityError):
        store.operator_job(job_id, apply=True, **inputs)
    assert store.operator_job(job_id, action="STATUS", now_ms=clock.now_ms())[0]["paid_call_state"] == "UNKNOWN"
    assert cutover_ops.generation_clear(settings)["result"] == "FAIL"
    with container.uow_factory().begin_immediate() as tx:
        tx.connection.execute("DROP TRIGGER fail_resolution")
    summary, _ = store.operator_job(job_id, apply=True, **inputs)
    assert summary["result"] == "RESOLVED"
    assert summary["resolved_by"] == "production-operator"
    assert summary["paid_call_state"] == "SETTLED" and summary["actual_minor"] == 6200
    assert store.operator_job(job_id, apply=True, **inputs)[0]["result"] == "ALREADY_RESOLVED"
    assert cutover_ops.generation_clear(settings) == {"result": "PASS", "open_generation_unknown": 0}
    assert container.cutover_readiness.execute("2026-11-27").reasons == readiness_before
    assert gates_before == [
        cutover_ops.pending_gate(settings, "2026-11-27", **options)["reasons"]
        for options in ({"require_disabled": True}, {"approved": True})
    ]
    assert container.content_jobs_worker.process_once().claimed == 0


def test_generation_adapter_known_failure_phases_are_not_unknown(tmp_path):
    from growth_engine.application.errors import DraftAfterProviderError, DraftBeforeProviderError

    for index, (error, paid_state) in enumerate((
        (DraftBeforeProviderError("draft_request"), "RELEASED"),
        (DraftAfterProviderError("provider_draft_json", "malformed and confidential"), "SETTLED"),
    )):
        case = tmp_path / str(index)
        case.mkdir()
        _, container, _, _ = _generation_recovery_fixture(case)

        class Adapter:
            image_provider = None

            def draft(self, request):
                raise error

        container.generate_package._generator = Adapter()
        container.queue_slot_generation.execute(date(2026, 11, 27))
        results = container.content_jobs_worker.process_once()
        assert results.failed == 1 and results.unknown == 0
        with container.uow_factory().read_only() as tx:
            paid = tx.connection.execute("SELECT state, provider_response_json FROM paid_calls").fetchone()
            assert paid["state"] == paid_state
            if paid_state == "SETTLED":
                evidence = json.loads(paid["provider_response_json"])
                assert evidence["response_received"] is True
                assert "confidential" not in paid["provider_response_json"]
            assert tx.connection.execute("SELECT count(*) FROM incidents").fetchone()[0] == 0
