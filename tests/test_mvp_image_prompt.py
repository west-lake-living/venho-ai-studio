"""Step 8 — MVP milestone (§16): DNA + brief -> valid, faithful, saved image prompt."""

from pathlib import Path

from prompt_studio.builders.image_prompt_builder import build_image_prompt
from prompt_studio.knowledge_reader import read_dna
from prompt_studio.prompt_store import save_prompt
from prompt_studio.schemas.image_prompt import ImagePromptContract
from prompt_studio.validator import validate_faithfulness, validate_structural

REAL_DNA = Path("data/projects/venho_hotel/knowledge/VENHO_HOTEL_LAKE_VIEW_ROOM_DNA.json")
BRIEF = "Create a realistic booking-style image of the lake view room."


def test_mvp_lake_view_room_booking_style_image_prompt(tmp_path):
    dna = read_dna(REAL_DNA)

    contract = build_image_prompt(dna, BRIEF, brief_slug="booking-style")

    structural = validate_structural(
        contract, dna_had_forbidden=bool(dna.forbidden), dna_had_allowed_imperfections=bool(dna.allowed_imperfections)
    )
    assert structural.passed, structural.errors

    faithfulness = validate_faithfulness(contract)
    assert faithfulness.passed, faithfulness.errors
    contract = contract.model_copy(
        update={"validation": contract.validation.model_copy(update={"structural": "pass", "faithfulness": "pass"})}
    )

    assert contract.forbidden, "MVP DoD: prompt must carry forbidden rules"
    assert contract.allowed_imperfections, "MVP DoD: prompt must carry allowed imperfections"

    # No invention beyond Knowledge: every required_dna value and every allowed_imperfection
    # traces back into final_prompt verbatim (builder pulls only from DNA + brief, §2.2).
    for item in contract.required_dna:
        assert item.value in contract.final_prompt
    for item in contract.allowed_imperfections:
        assert item.value in contract.final_prompt
    for item in contract.forbidden:
        assert item.rule in contract.negative_prompt

    paths = save_prompt(contract, root=tmp_path)
    reloaded = ImagePromptContract.model_validate_json(paths.json.read_text(encoding="utf-8"))
    assert reloaded.prompt_id == "lake_view_room__image__booking-style"
    assert reloaded.validation.faithfulness == "pass"
