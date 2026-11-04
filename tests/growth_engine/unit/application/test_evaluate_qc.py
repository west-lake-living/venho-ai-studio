from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from typing import Iterator

import pytest

from growth_engine.adapters.outbound.legacy.qc_adapter import LegacyQcAdapter
from growth_engine.application.dto import EffectiveQcPolicy, FactSnapshot, QcResult, VariantView
from growth_engine.application.errors import NotFound
from growth_engine.application.media.evaluate_qc import EvaluateQc, QcStatusPersistenceUnavailable
from growth_engine.domain.media.asset import MediaVariant, VariantQcStatus
from growth_engine.domain.media.qc import QcDecision, QcReport
from tests.growth_engine.support.fakes import FakeClock, FakeQc, SeqIds

_HASH_A = "a" * 64
_HASH_B = "b" * 64
_HASH_C = "c" * 64
_VARIANT_BYTES = b"synthetic-variant-bytes"
_VARIANT_SHA = sha256(_VARIANT_BYTES).hexdigest()


class _FakeMediaRepo:
    def __init__(self, variant: MediaVariant | None) -> None:
        self.variant = variant

    def get_variant(self, variant_id: str) -> MediaVariant | None:
        return self.variant if self.variant and self.variant.id == variant_id else None

    def save_variant_status(self, variant_id: str, status: VariantQcStatus) -> None:
        assert self.variant is not None and self.variant.id == variant_id
        self.variant = replace(self.variant, qc_status=status)


class _FakeQcRepo:
    def __init__(self) -> None:
        self.reports: list[QcReport] = []

    def save(self, report: QcReport) -> None:
        self.reports.append(report)


class _FakeUnitOfWork:
    def __init__(self, media: _FakeMediaRepo, qc: _FakeQcRepo) -> None:
        self.media = media
        self.qc = qc

    @contextmanager
    def read_only(self) -> Iterator[_FakeUnitOfWork]:
        yield self

    @contextmanager
    def begin_immediate(self) -> Iterator[_FakeUnitOfWork]:
        yield self


def test_evaluate_qc_persists_report_and_updates_variant_status() -> None:
    media = _FakeMediaRepo(_variant())
    qc_repo = _FakeQcRepo()
    uow = _FakeUnitOfWork(media, qc_repo)
    evaluator = FakeQc(_qc_result("PASS"))
    use_case = EvaluateQc(
        lambda: uow,
        evaluator,
        FakeClock(1234),
        SeqIds("qc-test"),
        variant_qc_status_updater=lambda tx, variant_id, status: tx.media.save_variant_status(variant_id, status),
    )
    facts = FactSnapshot({"_synthetic": "fixture"}, _HASH_C)

    report = use_case.execute(
        variant_id="variant-1",
        caption="Synthetic caption",
        facts=facts,
        project="venho_hotel",
        subject="outside",
    )

    assert report.decision is QcDecision.PASS
    assert report.caption_hash == sha256(b"Synthetic caption").hexdigest()
    assert report.fact_snapshot_hash == _HASH_C
    assert qc_repo.reports == [report]
    assert media.variant is not None and media.variant.qc_status is VariantQcStatus.PASS


def test_evaluate_qc_forbidden_is_hard_failure_even_if_fake_score_passes() -> None:
    media = _FakeMediaRepo(_variant())
    qc_repo = _FakeQcRepo()
    uow = _FakeUnitOfWork(media, qc_repo)
    result = _qc_result(
        "PASS",
        result_json='{"overall_score":100,"forbidden_violations":[{"rule":"_synthetic_rule","violated":true}]}',
    )
    use_case = EvaluateQc(
        lambda: uow,
        FakeQc(result),
        FakeClock(1234),
        SeqIds("qc-hard-fail"),
        variant_qc_status_updater=lambda tx, variant_id, status: tx.media.save_variant_status(variant_id, status),
    )

    report = use_case.execute(
        variant_id="variant-1",
        caption="Synthetic caption",
        facts=FactSnapshot({}, _HASH_C),
        project="venho_hotel",
        subject="outside",
    )

    assert report.decision is QcDecision.FAIL
    assert media.variant is not None and media.variant.qc_status is VariantQcStatus.FAIL


def test_evaluate_qc_coverage_gap_prevents_default_pass() -> None:
    media = _FakeMediaRepo(_variant())
    qc_repo = _FakeQcRepo()
    uow = _FakeUnitOfWork(media, qc_repo)
    use_case = EvaluateQc(
        lambda: uow,
        FakeQc(_qc_result("PASS", coverage_gaps=("technical_quality_detector_unverified",))),
        FakeClock(1234),
        SeqIds("qc-gap"),
        variant_qc_status_updater=lambda tx, variant_id, status: tx.media.save_variant_status(variant_id, status),
    )

    report = use_case.execute(
        variant_id="variant-1",
        caption="Synthetic caption",
        facts=FactSnapshot({}, _HASH_C),
        project="venho_hotel",
        subject="outside",
    )

    assert report.decision is QcDecision.REVIEW
    assert report.coverage_gaps == ("technical_quality_detector_unverified",)
    assert media.variant is not None and media.variant.qc_status is VariantQcStatus.REVIEW


def test_missing_variant_does_not_run_evaluator() -> None:
    media = _FakeMediaRepo(None)
    uow = _FakeUnitOfWork(media, _FakeQcRepo())
    evaluator = FakeQc(_qc_result("PASS"))
    use_case = EvaluateQc(
        lambda: uow,
        evaluator,
        FakeClock(1234),
        SeqIds("qc-missing"),
        variant_qc_status_updater=lambda tx, variant_id, status: tx.media.save_variant_status(variant_id, status),
    )

    with pytest.raises(NotFound):
        use_case.execute(
            variant_id="missing",
            caption="Synthetic caption",
            facts=FactSnapshot({}, _HASH_C),
            project="venho_hotel",
            subject="outside",
        )
    assert evaluator.result is not None
    assert not uow.qc.reports


def test_missing_qc_status_repository_method_fails_closed_and_rolls_back_report() -> None:
    media = _FakeMediaRepo(_variant())
    qc_repo = _FakeQcRepo()
    uow = _FakeUnitOfWork(media, qc_repo)
    use_case = EvaluateQc(lambda: uow, FakeQc(_qc_result("PASS")), FakeClock(1234), SeqIds("qc-no-writer"))

    with pytest.raises(QcStatusPersistenceUnavailable):
        use_case.execute(
            variant_id="variant-1",
            caption="Synthetic caption",
            facts=FactSnapshot({}, _HASH_C),
            project="venho_hotel",
            subject="outside",
        )

    assert not qc_repo.reports
    assert media.variant is not None and media.variant.qc_status is VariantQcStatus.PENDING


def test_legacy_qc_adapter_compiles_dna_hash_and_hard_forbidden(tmp_path: Path) -> None:
    _write_dna_config(tmp_path)
    adapter = LegacyQcAdapter(_FakeStore(_VARIANT_BYTES), base_dir=tmp_path, validator_fn=_approved_report)

    policy = adapter.compile_policy("test", "room", None)
    result = adapter.evaluate(_variant_view(), "Synthetic caption", FactSnapshot({}, _HASH_C), policy)

    assert policy.forbidden == ("no marble",)
    assert policy.ruleset_hash != "0" * 64
    assert result.decision == "REVIEW"
    assert "technical_quality_detector_unverified" in result.coverage_gaps
    assert result.caption_hash == sha256(b"Synthetic caption").hexdigest()
    assert result.fact_snapshot_hash == _HASH_C


def test_legacy_qc_adapter_forbidden_violation_overrides_approve(tmp_path: Path) -> None:
    _write_dna_config(tmp_path)

    def forbidden_report(project: str, subject: str, path: Path, **kwargs: object) -> object:
        return _approved_report(project, subject, path, forbidden_violations=[{"rule": "no marble", "violated": True}])

    adapter = LegacyQcAdapter(_FakeStore(_VARIANT_BYTES), base_dir=tmp_path, validator_fn=forbidden_report)
    policy = adapter.compile_policy("test", "room", None)

    result = adapter.evaluate(_variant_view(), "Synthetic caption", FactSnapshot({}, _HASH_C), policy)

    assert result.decision == "FAIL"
    assert "forbidden_violated:no marble" in result.coverage_gaps


class _FakeStore:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def open(self, object_key: str):
        from io import BytesIO

        assert object_key == "variants/" + _VARIANT_SHA[:2] + "/" + _VARIANT_SHA + ".jpg"
        return BytesIO(self.content)


def _variant() -> MediaVariant:
    return MediaVariant(
        id="variant-1",
        asset_id="asset-1",
        transform_version="synthetic-v1",
        sha256=_VARIANT_SHA,
        object_key=f"variants/{_VARIANT_SHA[:2]}/{_VARIANT_SHA}.jpg",
        width=64,
        height=48,
        mime="image/jpeg",
        byte_size=len(_VARIANT_BYTES),
        qc_status=VariantQcStatus.PENDING,
        created_at_ms=1,
    )


def _variant_view() -> VariantView:
    variant = _variant()
    return VariantView(
        variant_id=variant.id,
        sha256=variant.sha256,
        width=variant.width,
        height=variant.height,
        mime=variant.mime,
        object_key=variant.object_key,
        qc_status=variant.qc_status.value,
    )


def _qc_result(
    decision: str,
    *,
    coverage_gaps: tuple[str, ...] = (),
    result_json: str = '{"_synthetic":true}',
) -> QcResult:
    return QcResult(decision, "0" * 64, sha256(b"Synthetic caption").hexdigest(), _HASH_C, coverage_gaps, result_json)


def _write_dna_config(base_dir: Path) -> None:
    knowledge = base_dir / "data" / "projects" / "test" / "knowledge"
    knowledge.mkdir(parents=True)
    (knowledge / "TEST_ROOM_DNA.json").write_text(
        '{"contract_version":"1.1","mode":"B","project":"test","subject":"room",'
        '"dna_version":"1.0","schema_id":"universal","schema_version":"1.1",'
        '"prompt_version":"p1","generated_at":"2026-11-04T00:00:00", "source_images":[], '
        '"invariant":[],"variable":[],"allowed_imperfections":[], '
        '"forbidden":[{"rule":"no marble","source":"curated"}], '
        '"evidence":{"total_images":0,"weak_features":[]},"future_capture_notes":[],"curator_notes":[]} ',
        encoding="utf-8",
    )
    config = base_dir / "config"
    config.mkdir()
    (config / "validation.yaml").write_text("validation: {thresholds: {approve: 90}}\n", encoding="utf-8")


def _approved_report(project: str, subject: str, path: Path, **kwargs: object) -> object:
    report = SimpleNamespace(
        project=project,
        subject=subject,
        artifact_ref=SimpleNamespace(hash="sha256:" + _VARIANT_SHA),
        verdict=SimpleNamespace(value="approve"),
        recommendation=SimpleNamespace(value="approve"),
        overall_score=100,
        kill_switch=SimpleNamespace(triggered=False, reason=""),
        forbidden_violations=kwargs.get("forbidden_violations", []),
        validation_notes=["mocked validator; no network"],
        raw_observation={"_synthetic": True},
        observer=SimpleNamespace(provider="mock", model="mock", samples=1),
        source_knowledge=[],
        category_scores={},
        section_scores=[],
        allowed_imperfections_check=[],
        issues=[],
    )
    report.model_dump = lambda mode="json": {
        "project": project,
        "subject": subject,
        "artifact_sha256": report.artifact_ref.hash,
        "verdict": report.verdict.value,
        "recommendation": report.recommendation.value,
        "overall_score": report.overall_score,
        "kill_switch": {"triggered": report.kill_switch.triggered, "reason": report.kill_switch.reason},
        "forbidden_violations": report.forbidden_violations,
        "validation_notes": report.validation_notes,
        "raw_observation": report.raw_observation,
        "observer": {"provider": "mock", "model": "mock", "samples": 1},
    }
    return report
