from pathlib import Path

from prompt_studio.builders.seo_prompt_builder import build_seo_prompt
from prompt_studio.knowledge_reader import read_dna
from prompt_studio.prompt_rules import load_prompt_rules
from prompt_studio.validator import validate_faithfulness, validate_structural

WESTLAKE_DNA = Path("data/projects/venho_hotel/knowledge/VENHO_HOTEL_WESTLAKE_DNA.json")
BRIEF = "Write a blog post about hotels near West Lake Hanoi."
KEYWORD_INTENT = "khách sạn gần Hồ Tây"


def _build():
    dna = read_dna(WESTLAKE_DNA)
    contract = build_seo_prompt(
        dna, BRIEF, brief_slug="blog", keyword_intent=KEYWORD_INTENT,
        target_language="vi", generated_at="2026-07-08T00:00:00+00:00",
    )
    return dna, contract


def test_build_seo_prompt_has_keyword_intent_and_restrictions_not_negative_prompt():
    _dna, contract = _build()
    assert contract.prompt_type == "seo"
    assert contract.keyword_intent == KEYWORD_INTENT
    assert not hasattr(contract, "negative_prompt")
    assert contract.restrictions
    assert contract.prompt_id == "westlake__seo__blog"
    assert contract.target_language == "vi"


def test_final_prompt_has_seo_structure_internal_links_and_required_facts():
    dna, contract = _build()
    assert "Keyword intent:" in contract.final_prompt
    assert "SEO structure:" in contract.final_prompt
    assert "Internal link hints:" in contract.final_prompt
    for item in dna.required_dna:
        assert item.value in contract.final_prompt


def test_restrictions_include_dna_forbidden_and_prompt_rules_restrictions():
    dna, contract = _build()
    dna_rules = load_prompt_rules("venho_hotel")
    for item in dna.forbidden:
        assert item.rule in contract.restrictions
    for text in dna_rules["restrictions"]:
        assert text in contract.restrictions


def test_seo_prompt_passes_structural_and_faithfulness_validation():
    dna, contract = _build()
    structural = validate_structural(
        contract, dna_had_forbidden=bool(dna.forbidden), dna_had_allowed_imperfections=bool(dna.allowed_imperfections)
    )
    assert structural.passed, structural.errors

    faithfulness = validate_faithfulness(contract)
    assert faithfulness.passed, faithfulness.errors


def test_build_seo_prompt_is_deterministic_across_two_runs():
    _dna, first = _build()
    _dna, second = _build()
    assert first.model_dump() == second.model_dump()
