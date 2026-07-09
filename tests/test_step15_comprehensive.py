"""Step 15 — comprehensive test with real Ven Ho DNA (§16):
lake_view_room image; linh_an+lake_view_room video; westlake content (vi); westlake seo (vi).

DoD: all four generate; Validate #2 passes; Knowledge is never modified; prompts are
usable as-is in AI tools; content/seo target the correct language.
"""

import hashlib
from pathlib import Path

from prompt_studio.optimizer_mock import optimize_mock
from prompt_studio.pipeline import run_content_pipeline, run_image_pipeline, run_seo_pipeline, run_video_pipeline
from prompt_studio.knowledge_reader import read_dna

KNOWLEDGE_DIR = Path("data/projects/venho_hotel/knowledge")
LAKE_VIEW_ROOM_DNA = KNOWLEDGE_DIR / "VENHO_HOTEL_LAKE_VIEW_ROOM_DNA.json"
LINH_AN_DNA = KNOWLEDGE_DIR / "VENHO_HOTEL_LINH_AN_DNA.json"
WESTLAKE_DNA = KNOWLEDGE_DIR / "VENHO_HOTEL_WESTLAKE_DNA.json"

ALL_KNOWLEDGE_FILES = list(KNOWLEDGE_DIR.glob("*.json"))


def _hash_all_knowledge() -> dict:
    return {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in ALL_KNOWLEDGE_FILES}


def test_all_four_prompt_types_generate_and_pass_validation_without_touching_knowledge(tmp_path):
    before = _hash_all_knowledge()

    image_result = run_image_pipeline(
        read_dna(LAKE_VIEW_ROOM_DNA),
        "Create a realistic booking-style image of the lake view room.",
        "booking-style",
        optimize_fn=optimize_mock,
        root=tmp_path,
    )
    video_result = run_video_pipeline(
        [read_dna(LAKE_VIEW_ROOM_DNA)],
        "A 15-second video of Linh An standing at the lake view room window at golden hour.",
        "window-15s",
        character_dna=read_dna(LINH_AN_DNA),
        optimize_fn=optimize_mock,
        root=tmp_path,
    )
    content_result = run_content_pipeline(
        read_dna(WESTLAKE_DNA),
        "Write a Facebook post about staying near West Lake.",
        "fb-stay",
        target_language="vi",
        optimize_fn=optimize_mock,
        root=tmp_path,
    )
    seo_result = run_seo_pipeline(
        read_dna(WESTLAKE_DNA),
        "Write a blog post about hotels near West Lake Hanoi.",
        "blog",
        "hotels near west lake hanoi",
        target_language="vi",
        optimize_fn=optimize_mock,
        root=tmp_path,
    )

    results = {"image": image_result, "video": video_result, "content": content_result, "seo": seo_result}

    # All four generated and saved.
    for name, result in results.items():
        assert result.paths is not None, f"{name}: expected a saved prompt"
        assert result.paths.markdown.exists()
        assert result.paths.json.exists()

    # Validate #2 (faithfulness) passed for all four.
    for name, result in results.items():
        assert result.faithfulness.passed, f"{name}: {result.faithfulness.errors}"
        assert result.contract.validation.faithfulness == "pass"
        assert not result.is_draft

    # Knowledge (DNA JSON) was never modified by generating prompts.
    after = _hash_all_knowledge()
    assert before == after

    # Prompts are directly usable: non-empty English instructions, no leftover placeholders.
    for name, result in results.items():
        final_prompt = result.contract.final_prompt
        assert final_prompt.strip()
        assert "{" not in final_prompt and "}" not in final_prompt, f"{name}: unresolved placeholder in final_prompt"

    # content/seo target the requested language (vi), instructions still say so in English.
    for name in ("content", "seo"):
        contract = results[name].contract
        assert contract.target_language == "vi"
        assert "Write the content in Vietnamese." in contract.final_prompt

    # image/video keep visual negative_prompt; content/seo use restrictions instead.
    assert results["image"].contract.negative_prompt
    assert results["video"].contract.negative_prompt
    assert results["content"].contract.restrictions
    assert results["seo"].contract.restrictions
