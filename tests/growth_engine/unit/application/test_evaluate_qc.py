from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Iterator

import pytest

from growth_engine.adapters.outbound.legacy.qc_adapter import LegacyQcAdapter, _normalize_qc_numbers
from growth_engine.application.dto import EffectiveQcPolicy, FactSnapshot, QcResult, VariantView
from growth_engine.application.errors import NotFound
from growth_engine.application.media.evaluate_qc import (
    EvaluateQc,
    QcPaidCallUnknown,
    QcPostResponseError,
    QcStatusPersistenceUnavailable,
)
from growth_engine.domain.media.asset import MediaVariant, VariantQcStatus
from growth_engine.domain.media.qc import QcDecision, QcReport
from growth_engine.domain.kernel.hashing import canonical_json_bytes
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


class _FakeBudgetRepo:
    def __init__(self) -> None:
        self.rows: dict[str, dict[str, object]] = {}

    def reserve(self, **values) -> bool:
        key = values["business_key"]
        if key in self.rows:
            return False
        self.rows[key] = {"state": "RESERVED", "reserved_minor": values["amount_minor"], "actual_minor": None, "provider_response_json": None}
        return True

    def get(self, key: str):
        return self.rows.get(key)

    def record_provider_response(self, key: str, *, response_json: str) -> bool:
        if key not in self.rows:
            return False
        self.rows[key]["provider_response_json"] = response_json
        return True

    def settle(self, key: str, *, actual_minor: int, settled_at_ms: int) -> bool:
        self.rows[key].update(state="SETTLED", actual_minor=actual_minor, settled_at=settled_at_ms)
        return True

    def mark_unknown(self, key: str) -> bool:
        self.rows[key]["state"] = "UNKNOWN"
        return True


class _FakeUnitOfWork:
    def __init__(self, media: _FakeMediaRepo, qc: _FakeQcRepo, budget: _FakeBudgetRepo | None = None) -> None:
        self.media = media
        self.qc = qc
        self.budget = budget or _FakeBudgetRepo()

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


def test_response_then_postprocess_failure_settles_and_retains_filtered_evidence(monkeypatch) -> None:
    from growth_engine.application.media import evaluate_qc as evaluate_qc_module

    class ResponseQc:
        def compile_policy(self, project, subject, scenario):
            return EffectiveQcPolicy(project, subject, scenario, "0" * 64, ("_synthetic_rule",))

        def evaluate(self, variant, caption, facts, policy, response_sink=None):
            response_sink({
                "source": "validator",
                "event": {
                    "validator": "image",
                    "rawResponse": '{"decision":"PASS","api_key":"secret","token":"hidden"',
                    "parseStatus": "raw_captured",
                },
            })
            response_sink({
                "source": "provider",
                "event": {"event": "response_received", "provider": "openai", "http_status": 200, "input_tokens": 1900, "output_tokens": 1111},
            })
            return _qc_result("PASS")

    monkeypatch.setattr(
        evaluate_qc_module,
        "_effective_decision",
        lambda *_args: (_ for _ in ()).throw(ValueError("postprocess failed with private provider body")),
    )
    budget = _FakeBudgetRepo()
    uow = _FakeUnitOfWork(_FakeMediaRepo(_variant()), _FakeQcRepo(), budget)
    use_case = EvaluateQc(
        lambda: uow,
        ResponseQc(),
        FakeClock(1234),
        SeqIds("qc-post-response"),
        variant_qc_status_updater=lambda tx, variant_id, status: tx.media.save_variant_status(variant_id, status),
        budget_policy=SimpleNamespace(monthly_cap_minor=10_000, currency="VND"),
        cost_estimate_minor=400,
    )

    with pytest.raises(QcPostResponseError) as caught:
        use_case.execute(
            variant_id="variant-1", caption="Synthetic caption", facts=FactSnapshot({}, _HASH_C),
            project="venho_hotel", subject="outside",
        )

    key = f"qc:{_VARIANT_SHA}:{sha256(b'Synthetic caption').hexdigest()}:{_HASH_C}:{'0' * 64}"
    row = budget.get(key)
    assert caught.value.code == "ERR_GC2_QC_POST_RESPONSE_FAILED"
    assert "ValueError" in caught.value.public_message
    assert "private provider body" not in caught.value.public_message
    assert row["state"] == "SETTLED"
    assert row["actual_minor"] == 400
    assert "1900" in row["provider_response_json"] and "1111" in row["provider_response_json"]
    assert "[REDACTED]" in row["provider_response_json"]
    assert "secret" not in row["provider_response_json"]


def test_failure_before_confirmed_response_remains_unknown() -> None:
    class BeforeResponseQc:
        def compile_policy(self, project, subject, scenario):
            return EffectiveQcPolicy(project, subject, scenario, "0" * 64, ())

        def evaluate(self, variant, caption, facts, policy, response_sink=None):
            raise TimeoutError("transport timed out")

    budget = _FakeBudgetRepo()
    uow = _FakeUnitOfWork(_FakeMediaRepo(_variant()), _FakeQcRepo(), budget)
    use_case = EvaluateQc(
        lambda: uow,
        BeforeResponseQc(),
        FakeClock(1234),
        SeqIds("qc-pre-response"),
        budget_policy=SimpleNamespace(monthly_cap_minor=10_000, currency="VND"),
        cost_estimate_minor=400,
    )

    with pytest.raises(QcPaidCallUnknown):
        use_case.execute(
            variant_id="variant-1", caption="Synthetic caption", facts=FactSnapshot({}, _HASH_C),
            project="venho_hotel", subject="outside",
        )
    row = next(iter(budget.rows.values()))
    assert row["state"] == "UNKNOWN"
    assert row["actual_minor"] is None


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


def test_legacy_qc_adapter_forwards_provider_response_evidence(tmp_path: Path) -> None:
    _write_dna_config(tmp_path)
    events = []

    def response_validator(
        project: str, subject: str, path: Path, *, raw_response_sink, transport_event_sink, **kwargs: object
    ) -> object:
        raw_response_sink({"parseStatus": "raw_captured", "rawResponse": '{"verdict":"approve"}'})
        transport_event_sink({"event": "response_received", "http_status": 200, "input_tokens": 1900})
        return _approved_report(project, subject, path)

    adapter = LegacyQcAdapter(
        _FakeStore(_VARIANT_BYTES), base_dir=tmp_path, validator_fn=response_validator
    )
    policy = adapter.compile_policy("test", "room", None)
    adapter.evaluate(
        _variant_view(), "Synthetic caption", FactSnapshot({}, _HASH_C), policy,
        response_sink=events.append,
    )

    assert events == [
        {"source": "validator", "event": {"parseStatus": "raw_captured", "rawResponse": '{"verdict":"approve"}'}},
        {"source": "provider", "event": {"event": "response_received", "http_status": 200, "input_tokens": 1900}},
    ]


def test_legacy_qc_adapter_reprocesses_saved_observation_without_validator_call(tmp_path: Path, monkeypatch) -> None:
    _write_dna_config(tmp_path)
    parsed = {}

    def report_from_observation(project, subject, image_path, observations, provider):
        parsed["observation"] = observations[0]
        return _approved_report(project, subject, image_path)

    monkeypatch.setattr(
        "growth_engine.adapters.outbound.legacy.qc_adapter.report_from_image_observations",
        report_from_observation,
    )

    def forbidden_provider_call(*args, **kwargs):
        raise AssertionError("saved evidence reprocessing must not call the validator/provider")

    adapter = LegacyQcAdapter(
        _FakeStore(_VARIANT_BYTES), base_dir=tmp_path, validator_fn=forbidden_provider_call, provider="openai"
    )
    policy = adapter.compile_policy("test", "room", None)
    response = (
        "Stored response:\n```json\n"
        '{"dna_matches":[{"key":"window_frame","match_state":"MATCH","confidence":"0.9"}]}'
        "\n```\nEnd."
    )
    result = adapter.reprocess_response(
        _variant_view(), "Synthetic caption", FactSnapshot({}, _HASH_C), policy, response
    )

    assert parsed["observation"].dna_matches[0].match_state.value == "match"
    assert result.decision == "REVIEW"
    assert result.ruleset_hash == policy.ruleset_hash


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


def test_qc_report_floats_are_renamed_and_encoded_as_basis_points() -> None:
    encoded = _normalize_qc_numbers({
        "validator_report": {
            "overall_score": 92.5,
            "dna_match_score": 0.00005,
            "category_scores": {"material": 88.125},
            "section_scores": [{"score": 0.00015}],
            "forbidden_violations": [{"confidence": 0.92}],
        }
    })
    assert encoded == {
        "validator_report": {
            "overall_score_bp": 925_000,
            "dna_match_score_bp": 0,
            "category_scores_bp": {"material": 881_250},
            "section_scores": [{"score_bp": 2}],
            "forbidden_violations": [{"confidence_bp": 9_200}],
        }
    }
    canonical_json_bytes(encoded)


def test_qc_non_finite_report_value_fails_with_field_path_and_code() -> None:
    from growth_engine.adapters.outbound.legacy.qc_adapter import QcNonFiniteNumberError

    with pytest.raises(QcNonFiniteNumberError, match=r"field \$\.validator_report\.section_scores\[0\]\.score") as error:
        _normalize_qc_numbers({"validator_report": {"section_scores": [{"score": float("inf")}]}})
    assert error.value.code == "ERR_GC2_QC_NONFINITE_NUMBER"


def test_legacy_qc_adapter_result_is_canonical_json_after_float_normalization(tmp_path: Path) -> None:
    report = _approved_report("test", "room", tmp_path / "unused.jpg")
    report.model_dump = lambda mode="json": {
        "overall_score": 92.5,
        "dna_match_score": 91.25,
        "category_scores": {"material": 88.0},
        "section_scores": [{"score": 90.5}],
        "forbidden_violations": [{"confidence": 0.92}],
        "raw_observation": {"dna_matches": [{"confidence_bp": 9_200}]},
    }
    adapter = LegacyQcAdapter(_FakeStore(_VARIANT_BYTES), base_dir=tmp_path)
    policy = EffectiveQcPolicy("test", "room", None, _HASH_A, ())

    result = adapter._result_from_report(
        report,
        _variant_view(),
        "Synthetic caption",
        FactSnapshot({}, _HASH_C),
        policy,
    )
    payload = json.loads(result.result_json)
    canonical_json_bytes(payload)
    validator_report = payload["validator_report"]
    assert validator_report["overall_score_bp"] == 925_000
    assert validator_report["dna_match_score_bp"] == 912_500
    assert validator_report["category_scores_bp"]["material"] == 880_000
    assert validator_report["section_scores"][0]["score_bp"] == 905_000
    assert validator_report["forbidden_violations"][0]["confidence_bp"] == 9_200
