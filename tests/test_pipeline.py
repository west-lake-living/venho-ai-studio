from pathlib import Path

import pytest

import prompt_studio.validator as validator_module
from prompt_studio.knowledge_reader import KnowledgeDna, read_dna
from prompt_studio.optimizer import OptimizerDisabled
from prompt_studio.optimizer_mock import optimize_mock
from prompt_studio.pipeline import FaithfulnessValidationFailed, StructuralValidationFailed, run_image_pipeline
from shared.vision.errors import SchemaValidationError
from validator_studio.module02_integration import score_module02_prompt_contract

REAL_DNA = Path("data/projects/venho_hotel/knowledge/VENHO_HOTEL_LAKE_VIEW_ROOM_DNA.json")
BRIEF = "Create a realistic booking-style image of the lake view room."


def _dna():
    return read_dna(REAL_DNA)


def test_pipeline_build_v1_optimize_v2_render_order_with_mock_optimizer(tmp_path):
    result = run_image_pipeline(_dna(), BRIEF, "booking-style", optimize_fn=optimize_mock, root=tmp_path)

    assert result.structural.passed
    assert result.faithfulness.passed
    assert result.used_optimizer is True
    assert result.contract.optimizer.provider == "mock"
    assert result.contract.validation.structural == "pass"
    assert result.contract.validation.faithfulness == "pass"
    assert result.paths is not None
    assert result.paths.markdown.exists()
    assert result.paths.json.exists()


def test_pipeline_reverts_to_deterministic_when_optimizer_breaks_faithfulness(tmp_path):
    dna = _dna()

    def evil_optimize(contract):
        return contract.model_copy(
            update={
                "final_prompt": "A vague prompt that drops every specific detail.",
                "optimizer": contract.optimizer.model_copy(update={"used": True, "provider": "evil", "model": "evil", "temperature": 0}),
            }
        )

    result = run_image_pipeline(dna, BRIEF, "booking-style", optimize_fn=evil_optimize, root=tmp_path)

    assert result.used_optimizer is False
    assert result.faithfulness.passed
    assert any("reverted to deterministic" in note for note in result.notes)
    for item in dna.required_dna:
        assert item.value in result.contract.final_prompt


def test_pipeline_falls_back_when_optimizer_raises(tmp_path):
    def broken_optimize(contract):
        raise SchemaValidationError("optimizer produced garbage")

    result = run_image_pipeline(_dna(), BRIEF, "booking-style", optimize_fn=broken_optimize, root=tmp_path)

    assert result.used_optimizer is False
    assert result.faithfulness.passed
    assert any("optimizer failed" in note for note in result.notes)


def test_pipeline_skips_silently_when_optimizer_disabled(tmp_path):
    def disabled_optimize(contract):
        raise OptimizerDisabled("optimizer.enabled is false")

    result = run_image_pipeline(_dna(), BRIEF, "booking-style", optimize_fn=disabled_optimize, root=tmp_path)

    assert result.used_optimizer is False
    assert result.notes == []
    assert result.faithfulness.passed


def test_pipeline_raises_faithfulness_error_when_deterministic_also_fails_and_no_draft_allowed(tmp_path, monkeypatch):
    monkeypatch.setattr(validator_module, "max_length_for", lambda prompt_type: 1)

    with pytest.raises(FaithfulnessValidationFailed):
        run_image_pipeline(_dna(), BRIEF, "booking-style", optimize_fn=optimize_mock, allow_draft=False, root=tmp_path)


def test_pipeline_exports_draft_when_allow_draft_true(tmp_path, monkeypatch):
    monkeypatch.setattr(validator_module, "max_length_for", lambda prompt_type: 1)

    result = run_image_pipeline(_dna(), BRIEF, "booking-style", optimize_fn=optimize_mock, allow_draft=True, root=tmp_path)

    assert result.is_draft is True
    assert not result.faithfulness.passed
    assert result.paths is not None
    assert any("DRAFT" in note for note in result.notes)


def test_pipeline_raises_structural_error_when_dna_has_no_invariants(tmp_path):
    empty_dna = KnowledgeDna(
        path=Path("fake.json"),
        project="venho_hotel",
        subject="empty_subject",
        dna_version="1.0",
        contract_version="1.1",
        content_hash="deadbeef",
        required_dna=[],
        allowed_variations=[],
        allowed_imperfections=[],
        forbidden=[],
    )
    with pytest.raises(StructuralValidationFailed):
        run_image_pipeline(empty_dna, BRIEF, "empty", optimize_fn=optimize_mock, root=tmp_path)


def test_pipeline_can_attach_module03_advisory_report_without_becoming_gate(tmp_path):
    result = run_image_pipeline(
        _dna(),
        BRIEF,
        "booking-style",
        optimize_fn=optimize_mock,
        root=tmp_path,
        advisory_fn=score_module02_prompt_contract,
    )

    assert result.faithfulness.passed
    assert result.advisory_report is not None
    assert result.advisory_report.module == "validator_studio"
    assert result.advisory_report.validation_type == "prompt"


def test_pipeline_continues_when_advisory_hook_fails(tmp_path):
    def broken_advisory(_contract):
        raise RuntimeError("scorer unavailable")

    result = run_image_pipeline(
        _dna(),
        BRIEF,
        "booking-style",
        optimize_fn=optimize_mock,
        root=tmp_path,
        advisory_fn=broken_advisory,
    )

    assert result.faithfulness.passed
    assert result.advisory_report is None
    assert any("advisory validation failed" in note for note in result.notes)
