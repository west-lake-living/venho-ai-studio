from __future__ import annotations

from pathlib import Path
from shutil import copyfile

import pytest

from content_studio.builders.social_builder import ForbiddenContentError, build_social_draft
from content_studio.campaign_generator import generate_campaign
from content_studio.content_calendar import build_calendar
from content_studio.content_context import load_content_config
from content_studio.content_engine import generate_content
from content_studio.content_manifest import mark_stale_sources
from content_studio.prompt_bridge import build_content_prompt_for_request
from content_studio.schemas.content_request import ContentRequest, SourceKnowledgeRef


def _request() -> ContentRequest:
    return ContentRequest(
        project="venho_hotel",
        content_type="facebook_post",
        topic="Morning at West Lake",
        target_audience="Vietnamese leisure guests",
        content_pillar="Khám phá Hồ Tây",
        tone="warm, clear, trustworthy",
        target_language="vi",
        cta_type="booking_soft",
        source_knowledge=[
            SourceKnowledgeRef(
                file="VENHO_HOTEL_WESTLAKE_DNA.json",
                dna_version="1.0",
                hash="sha256:test",
            )
        ],
    )


def _tmp_data_root(tmp_path: Path) -> Path:
    root = tmp_path / "data" / "projects"
    knowledge_dir = root / "venho_hotel" / "knowledge"
    knowledge_dir.mkdir(parents=True)
    copyfile(
        Path("data/projects/venho_hotel/knowledge/VENHO_HOTEL_WESTLAKE_DNA.json"),
        knowledge_dir / "VENHO_HOTEL_WESTLAKE_DNA.json",
    )
    return root


def test_content_config_loads_without_forbidden_or_cta() -> None:
    config = load_content_config("venho_hotel")
    assert "content_pillars" in config
    content_dir = Path("config/projects/venho_hotel/content")
    assert not (content_dir / "forbidden_claims.yaml").exists()
    assert not (content_dir / "cta_rules.yaml").exists()


def test_prompt_bridge_uses_module02_content_prompt(tmp_path: Path) -> None:
    result = build_content_prompt_for_request(_request(), data_root=Path("data/projects"), prompts_root=tmp_path)
    assert result.contract.module == "prompt_studio"
    assert result.contract.prompt_type == "content"
    assert result.contract.target_language == "vi"
    assert result.json_path.exists()
    assert "Write the content in Vietnamese" in result.contract.final_prompt


def test_social_builder_prefilters_forbidden(tmp_path: Path) -> None:
    bridge = build_content_prompt_for_request(_request(), data_root=Path("data/projects"), prompts_root=tmp_path)

    def bad_generator(request, prompt, config):
        return {
            "title": "Bad",
            "hook": "Best in Hanoi",
            "body": "This is a 5 star luxury resort claim.",
            "cta": "Book now",
            "hashtags": [],
            "visual_note": "None",
        }

    with pytest.raises(ForbiddenContentError):
        build_social_draft(_request(), bridge.contract, {}, generator_fn=bad_generator)


def test_content_engine_generates_social_draft_end_to_end(tmp_path: Path) -> None:
    result = generate_content(_request(), data_root=_tmp_data_root(tmp_path), config_root=Path("config/projects"), validate=False)
    assert result.output.module == "content_studio"
    assert result.output.status == "draft"
    assert result.output.source_prompt.file
    assert result.output.validation.status == "pending"
    assert result.markdown_path.exists()
    assert result.json_path.exists()
    assert result.manifest_path.exists()
    assert "## SOURCE PROMPT" in result.markdown_path.read_text(encoding="utf-8")


@pytest.mark.parametrize("content_type", ["blog", "website", "ota", "faq", "email"])
def test_content_engine_generates_all_planned_content_types(tmp_path: Path, content_type: str) -> None:
    request = _request().model_copy(update={"content_type": content_type, "keyword": "khách sạn gần Hồ Tây"})
    result = generate_content(request, data_root=_tmp_data_root(tmp_path), config_root=Path("config/projects"), validate=False)
    assert result.output.content_type == content_type
    assert result.output.payload
    assert result.markdown_path.exists()
    assert "## STRUCTURED PAYLOAD" in result.markdown_path.read_text(encoding="utf-8")


def test_campaign_generator_uses_one_message_core_for_multiple_channels(tmp_path: Path) -> None:
    result = generate_campaign(
        _request(),
        ["facebook", "instagram", "threads"],
        data_root=_tmp_data_root(tmp_path),
        config_root=Path("config/projects"),
        validate=False,
    )
    assert "Morning at West Lake" in result.message_core
    assert [item.output.content_type for item in result.results] == [
        "facebook_post",
        "instagram_post",
        "threads_post",
    ]
    assert all(item.markdown_path.exists() for item in result.results)


def test_content_calendar_builds_month_from_cadence_and_pillars(tmp_path: Path) -> None:
    result = build_calendar(
        "venho_hotel",
        "2026-08",
        data_root=_tmp_data_root(tmp_path),
        config_root=Path("config/projects"),
    )
    assert result.entries
    assert result.json_path.exists()
    assert result.markdown_path.exists()
    assert {"date", "channel", "topic", "pillar", "required_asset", "cta"} <= set(result.entries[0])


def test_manifest_marks_source_updated(tmp_path: Path) -> None:
    data_root = _tmp_data_root(tmp_path)
    generated = generate_content(_request(), data_root=data_root, config_root=Path("config/projects"), validate=False)
    stale = mark_stale_sources("venho_hotel", {"VENHO_HOTEL_WESTLAKE_DNA.json": "sha256:new"}, root=data_root)
    assert stale.stale_count == 1
    assert "source_updated" in generated.manifest_path.read_text(encoding="utf-8")
