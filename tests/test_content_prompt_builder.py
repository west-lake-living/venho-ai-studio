from pathlib import Path

from prompt_studio.builders.content_prompt_builder import build_content_prompt
from prompt_studio.knowledge_reader import read_dna
from prompt_studio.prompt_rules import load_prompt_rules
from prompt_studio.validator import validate_faithfulness, validate_structural

WESTLAKE_DNA = Path("data/projects/venho_hotel/knowledge/VENHO_HOTEL_WESTLAKE_DNA.json")
BRIEF = "Write a Facebook post about staying near West Lake."


def _build(target_language=None):
    dna = read_dna(WESTLAKE_DNA)
    return dna, build_content_prompt(
        dna, BRIEF, brief_slug="fb-stay", target_language=target_language, generated_at="2026-07-08T00:00:00+00:00"
    )


def test_build_content_prompt_has_no_negative_prompt_but_has_restrictions():
    _dna, contract = _build()
    assert contract.prompt_type == "content"
    assert not hasattr(contract, "negative_prompt")
    assert contract.restrictions
    assert contract.prompt_id == "westlake__content__fb-stay"


def test_target_language_defaults_from_prompt_rules_and_can_be_overridden():
    dna_rules = load_prompt_rules("venho_hotel")
    _dna, default_contract = _build()
    assert default_contract.target_language == dna_rules["default_target_language"]

    _dna, vi_contract = _build(target_language="vi")
    assert vi_contract.target_language == "vi"


def test_restrictions_include_dna_forbidden_and_prompt_rules_restrictions():
    dna, contract = _build()
    dna_rules = load_prompt_rules("venho_hotel")
    for item in dna.forbidden:
        assert item.rule in contract.restrictions
    for text in dna_rules["restrictions"]:
        assert text in contract.restrictions


def test_final_prompt_has_audience_tone_brand_dna_cta_and_required_facts():
    dna, contract = _build()
    assert "Audience:" in contract.final_prompt
    assert "Tone:" in contract.final_prompt
    assert "Brand DNA:" in contract.final_prompt
    assert "Call-to-action:" in contract.final_prompt
    for item in dna.required_dna:
        assert item.value in contract.final_prompt


def test_content_prompt_passes_structural_and_faithfulness_validation():
    dna, contract = _build()
    structural = validate_structural(
        contract, dna_had_forbidden=bool(dna.forbidden), dna_had_allowed_imperfections=bool(dna.allowed_imperfections)
    )
    assert structural.passed, structural.errors

    faithfulness = validate_faithfulness(contract)
    assert faithfulness.passed, faithfulness.errors


def test_build_content_prompt_is_deterministic_across_two_runs():
    _dna, first = _build()
    _dna, second = _build()
    assert first.model_dump() == second.model_dump()
