from __future__ import annotations

import hashlib
import sqlite3
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
