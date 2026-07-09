from prompt_studio.schemas.content_prompt import ContentPromptContract
from prompt_studio.schemas.image_prompt import ImagePromptContract
from prompt_studio.schemas.seo_prompt import SeoPromptContract
from prompt_studio.schemas.video_prompt import VideoPromptContract

SAMPLE_IMAGE = {
    "contract_version": "1.0",
    "module": "prompt_studio",
    "project": "venho_hotel",
    "prompt_type": "image",
    "prompt_id": "lake_view_room__image__booking-style",
    "prompt_version": "1.0",
    "generated_at": "2026-07-08T00:00:00",
    "source_knowledge": [
        {
            "file": "VENHO_LAKE_VIEW_ROOM_DNA.json",
            "dna_version": "1.0",
            "dna_contract_version": "1.1",
            "hash": "sha256:deadbeef",
        }
    ],
    "template": {"name": "image_prompt.yaml", "template_version": "1.0"},
    "task_brief": "Create a realistic booking-style image of the lake view room.",
    "target_language": "en",
    "required_dna": [
        {"key": "window_frame", "value": "matte black aluminum window frame"}
    ],
    "allowed_variations": [
        {"key": "lighting", "value_range": ["morning daylight", "indoor warm light"]}
    ],
    "allowed_imperfections": [
        {"value": "minor scuff marks on skirting boards", "source": "curated"}
    ],
    "forbidden": [{"rule": "no floor-to-ceiling glass wall", "source": "curated"}],
    "final_prompt": "A realistic booking-style photo of the lake view room...",
    "negative_prompt": "no floor-to-ceiling glass wall",
    "optimizer": {"used": True, "provider": "claude", "model": "claude-sonnet-4-6", "temperature": 0},
    "validation": {"structural": "pass", "faithfulness": "pass"},
    "notes": [],
}


def test_image_prompt_contract_validates_sample_from_plan_section_7_1():
    contract = ImagePromptContract.model_validate(SAMPLE_IMAGE)
    assert contract.contract_version == "1.0"
    assert contract.prompt_type == "image"
    assert contract.prompt_id == "lake_view_room__image__booking-style"
    assert contract.target_language == "en"
    assert contract.required_dna[0].key == "window_frame"
    assert contract.validation.structural == "pass"


def test_video_prompt_contract_allows_multi_dna_fields_optional():
    payload = {**SAMPLE_IMAGE, "prompt_type": "video", "prompt_id": "linh_an__video__window-15s"}
    contract = VideoPromptContract.model_validate(payload)
    assert contract.character_lock is None
    assert contract.environment_dna is None


def test_content_prompt_contract_has_restrictions_not_negative_prompt():
    payload = {
        **SAMPLE_IMAGE,
        "prompt_type": "content",
        "prompt_id": "westlake__content__fb-stay",
        "target_language": "vi",
        "restrictions": ["không hứa 5 sao", "không nói 'sang chảnh nhất'"],
    }
    del payload["negative_prompt"]
    contract = ContentPromptContract.model_validate(payload)
    assert contract.restrictions == ["không hứa 5 sao", "không nói 'sang chảnh nhất'"]
    assert not hasattr(contract, "negative_prompt")


def test_seo_prompt_contract_requires_keyword_intent():
    payload = {
        **SAMPLE_IMAGE,
        "prompt_type": "seo",
        "prompt_id": "westlake__seo__blog",
        "target_language": "vi",
        "restrictions": ["không hứa 5 sao"],
        "keyword_intent": "khách sạn gần Hồ Tây",
    }
    del payload["negative_prompt"]
    contract = SeoPromptContract.model_validate(payload)
    assert contract.keyword_intent == "khách sạn gần Hồ Tây"
