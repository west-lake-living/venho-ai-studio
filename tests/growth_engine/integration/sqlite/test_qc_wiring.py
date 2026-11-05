from __future__ import annotations

import hashlib
from pathlib import Path

from growth_engine.adapters.outbound.persistence.sqlite.connection import connect
from growth_engine.adapters.outbound.persistence.sqlite.migrator import MigrationRunner
from growth_engine.adapters.outbound.persistence.sqlite.uow import SqliteUnitOfWork
from growth_engine.application.dto import FactSnapshot, QcResult
from growth_engine.application.media.evaluate_qc import EvaluateQc
from growth_engine.domain.media.asset import MediaAsset, MediaVariant, VariantQcStatus
from growth_engine.domain.media.qc import QcDecision
from tests.growth_engine.support.fakes import FakeClock, FakeQc, SeqIds


def test_evaluate_qc_atomically_persists_report_and_variant_status(tmp_path: Path) -> None:
    database = tmp_path / "growth.db"
    connection = connect(database)
    try:
        MigrationRunner(Path("growth_engine/adapters/outbound/persistence/sqlite/migrations")).apply(
            connection, application_version="pytest"
        )
    finally:
        connection.close()
    uow = SqliteUnitOfWork(lambda: connect(database), sleep=lambda _: None)
    image = b"synthetic-approved-jpeg"
    image_sha = hashlib.sha256(image).hexdigest()
    variant = MediaVariant(
        id="variant-synthetic",
        asset_id="asset-synthetic",
        transform_version="synthetic-v1",
        sha256=image_sha,
        object_key=f"variants/{image_sha[:2]}/{image_sha}.jpg",
        width=80,
        height=100,
        mime="image/jpeg",
        byte_size=len(image),
        qc_status=VariantQcStatus.PENDING,
        created_at_ms=1,
    )
    with uow.begin_immediate() as tx:
        tx.media.save_asset(
            MediaAsset(
                id="asset-synthetic",
                source_type="upload",
                source_ref="synthetic-upload",
                source_revision="r1",
                source_sha256=image_sha,
                original_key="originals/synthetic.jpg",
                metadata_json='{"_synthetic":true}',
                created_at_ms=1,
            )
        )
        tx.media.save_variant(variant)

    caption_hash = hashlib.sha256(b"Synthetic caption").hexdigest()
    facts_hash = hashlib.sha256(b"{}").hexdigest()
    evaluator = FakeQc(
        QcResult(
            decision="PASS",
            ruleset_hash="0" * 64,
            caption_hash=caption_hash,
            fact_snapshot_hash=facts_hash,
            result_json='{"_synthetic":true}',
        )
    )
    report = EvaluateQc(
        lambda: uow, evaluator, FakeClock(1234), SeqIds("qc-synthetic")
    ).execute(
        variant_id=variant.id,
        caption="Synthetic caption",
        facts=FactSnapshot({"_synthetic": True}, facts_hash),
        project="venho_hotel",
        subject="outside",
    )

    with uow.read_only() as tx:
        stored_variant = tx.media.get_variant(variant.id)
        stored_report = tx.qc.get(report.id)
    assert stored_variant is not None and stored_variant.qc_status is VariantQcStatus.PASS
    assert stored_report is not None and stored_report.decision is QcDecision.PASS
