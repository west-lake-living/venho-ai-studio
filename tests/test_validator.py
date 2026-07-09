from pathlib import Path

from prompt_studio.builders.image_prompt_builder import build_image_prompt
from prompt_studio.knowledge_reader import read_dna
from prompt_studio.validator import validate_faithfulness, validate_structural

REAL_DNA = Path("data/projects/venho_hotel/knowledge/VENHO_HOTEL_LAKE_VIEW_ROOM_DNA.json")
BRIEF = "Create a realistic booking-style image of the lake view room."


def _build():
    dna = read_dna(REAL_DNA)
    contract = build_image_prompt(dna, BRIEF, brief_slug="booking-style", generated_at="2026-07-08T00:00:00+00:00")
    return dna, contract


def test_structural_and_faithfulness_pass_for_builder_output():
    dna, contract = _build()
    structural = validate_structural(
        contract,
        dna_had_forbidden=bool(dna.forbidden),
        dna_had_allowed_imperfections=bool(dna.allowed_imperfections),
    )
    assert structural.passed, structural.errors

    faithfulness = validate_faithfulness(contract)
    assert faithfulness.passed, faithfulness.errors


def test_structural_fails_when_forbidden_dropped_but_dna_had_forbidden():
    dna, contract = _build()
    stripped = contract.model_copy(update={"forbidden": []})
    result = validate_structural(stripped, dna_had_forbidden=bool(dna.forbidden), dna_had_allowed_imperfections=False)
    assert not result.passed
    assert any("forbidden" in e for e in result.errors)


def test_faithfulness_fails_when_required_dna_value_missing_from_final_prompt():
    _dna, contract = _build()
    mutated = contract.model_copy(update={"final_prompt": "A vague prompt with no specifics."})
    result = validate_faithfulness(mutated)
    assert not result.passed
    assert any("required_dna" in e for e in result.errors)


def test_faithfulness_fails_when_forbidden_rule_missing_from_negative_prompt():
    _dna, contract = _build()
    mutated = contract.model_copy(update={"negative_prompt": "something unrelated"})
    result = validate_faithfulness(mutated)
    assert not result.passed
    assert any("negative_prompt" in e for e in result.errors)


def test_faithfulness_fails_when_final_prompt_exceeds_max_length():
    _dna, contract = _build()
    mutated = contract.model_copy(update={"final_prompt": contract.final_prompt + ("x" * 1800)})
    result = validate_faithfulness(mutated)
    assert not result.passed
    assert any("exceeds max_length" in e for e in result.errors)


def test_faithfulness_passes_when_final_prompt_only_has_a_vietnamese_proper_noun():
    """A brand name like 'Ven Hồ Hotel' embedded in English instructions must not trip
    the language check — only prose actually written in Vietnamese should (§10)."""
    _dna, contract = _build()
    mutated = contract.model_copy(update={"final_prompt": contract.final_prompt + " Presented by Ven Hồ Hotel."})
    result = validate_faithfulness(mutated)
    assert not any("Vietnamese" in e for e in result.errors)


def test_faithfulness_fails_when_final_prompt_is_written_in_vietnamese():
    _dna, contract = _build()
    vietnamese_paragraph = (
        "Khách sạn Ven Hồ nằm ngay bên bờ Hồ Tây, không gian ấm áp và yên tĩnh, "
        "rất phù hợp cho một kỳ nghỉ thư giãn cuối tuần cùng gia đình và bạn bè thân thiết."
    )
    mutated = contract.model_copy(update={"final_prompt": vietnamese_paragraph})
    result = validate_faithfulness(mutated)
    assert not result.passed
    assert any("Vietnamese" in e for e in result.errors)
