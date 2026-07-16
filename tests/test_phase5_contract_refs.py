from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from shutil import copyfile

from content_studio.builders.social_builder import build_social_draft
from content_studio.generators.claude_generator import claude_longform_generator
from content_studio.prompt_bridge import build_content_prompt_for_request
from content_studio.schemas.content_request import ContentRequest, SourceKnowledgeRef
from prompt_studio.builders.video_prompt_builder import build_video_prompt
from prompt_studio.knowledge_reader import read_dna
from validator_studio.prompt_validator import build_prompt_validation_report
from validator_studio.utils import sha256_file
from video_studio.schemas.video_request import SourceKnowledgeRef as VideoSourceRef
from video_studio.schemas.video_request import VideoRequest
from video_studio.video_engine import generate_video_package


def _content_request(outfit_id: str = "nike_pink_running") -> ContentRequest:
    return ContentRequest(
        project="venho_hotel",
        content_type="facebook_post",
        topic="Linh An chạy bộ Hồ Tây",
        target_audience="Vietnamese leisure guests",
        content_pillar="Khám phá Hồ Tây",
        tone="warm, clear, trustworthy",
        target_language="vi",
        cta_type="booking_soft",
        subject="westlake",
        outfit_id=outfit_id,
        source_knowledge=[
            SourceKnowledgeRef(file="VENHO_HOTEL_WESTLAKE_DNA.json", dna_version="1.0", hash="sha256:test")
        ],
    )


def test_m02_m05_m03_trace_outfit_id_without_inference(tmp_path: Path) -> None:
    bridge = build_content_prompt_for_request(_content_request(), data_root=Path("data/projects"), prompts_root=tmp_path)

    assert bridge.contract.contract_refs
    assert bridge.contract.contract_refs.outfit
    assert bridge.contract.contract_refs.outfit.outfit_id == "nike_pink_running"
    assert "outfit_id: nike_pink_running" in bridge.contract.final_prompt

    output = build_social_draft(_content_request(), bridge.contract, {}, source_prompt_file=str(bridge.json_path))
    assert output.contract_refs
    assert output.contract_refs.outfit
    assert output.contract_refs.outfit.outfit_id == "nike_pink_running"

    dna_path = Path("data/projects/venho_hotel/knowledge/VENHO_HOTEL_WESTLAKE_DNA.json")
    report = build_prompt_validation_report(
        project="venho_hotel",
        subject="westlake",
        prompt=bridge.contract.model_dump(mode="json"),
        dna=json.loads(dna_path.read_text(encoding="utf-8")),
        prompt_file=str(bridge.json_path),
        dna_file=str(dna_path),
        dna_hash=sha256_file(dna_path),
    )
    assert report.contract_refs
    assert report.contract_refs.outfit
    assert report.contract_refs.outfit.outfit_id == "nike_pink_running"


def test_m06_video_locks_outfit_id_across_scene_prompts_and_package(tmp_path: Path) -> None:
    data_root = tmp_path / "data" / "projects"
    knowledge_dir = data_root / "venho_hotel" / "knowledge"
    knowledge_dir.mkdir(parents=True)
    for name in ["VENHO_HOTEL_LAKE_VIEW_ROOM_DNA.json", "VENHO_HOTEL_LINH_AN_DNA.json"]:
        copyfile(Path("data/projects/venho_hotel/knowledge") / name, knowledge_dir / name)

    def source_ref(name: str) -> VideoSourceRef:
        dna = read_dna(knowledge_dir / name)
        return VideoSourceRef(file=name, dna_version=dna.dna_version, hash=f"sha256:{dna.content_hash}")

    request = VideoRequest(
        project="venho_hotel",
        video_type="character",
        topic="Linh An morning run",
        duration_seconds=15,
        aspect_ratio="9:16",
        platform="instagram_reels",
        include_character=True,
        target_audience="Vietnamese leisure guests",
        source_knowledge=[
            source_ref("VENHO_HOTEL_LAKE_VIEW_ROOM_DNA.json"),
            source_ref("VENHO_HOTEL_LINH_AN_DNA.json"),
        ],
        outfit_id="mint_green",
        validation_required=False,
    )
    result = generate_video_package(request, data_root=data_root, config_root=Path("config/projects"), validate=False)

    assert result.package.contract_refs
    assert result.package.contract_refs.outfit
    assert result.package.contract_refs.outfit.outfit_id == "mint_green"
    assert "outfit_id:mint_green" in result.package.continuity_keys
    assert "outfit_id: mint_green" in result.package.engine_prompt_full


def test_video_prompt_contract_keeps_package_10_compatible() -> None:
    env = read_dna(Path("data/projects/venho_hotel/knowledge/VENHO_HOTEL_WESTLAKE_DNA.json"))
    contract = build_video_prompt(
        environment_dnas=[env],
        task_brief="Create a short West Lake video.",
        brief_slug="westlake",
        outfit_id="nike_pink_running",
    )
    dumped = contract.model_dump(mode="json")
    assert dumped["contract_version"] == "1.0"
    assert dumped["contract_refs"]["outfit"]["outfit_id"] == "nike_pink_running"


def test_claude_adapter_uses_fake_client_without_paid_api(monkeypatch) -> None:
    calls = {}

    class FakeMessages:
        def create(self, **kwargs):
            calls.update(kwargs)
            return types.SimpleNamespace(
                content=[
                    types.SimpleNamespace(
                        text=json.dumps({"title": "T", "hook": "H", "body": "B", "cta": "C"})
                    )
                ]
            )

    class FakeAnthropic:
        def __init__(self, api_key: str):
            self.api_key = api_key
            self.messages = FakeMessages()

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "anthropic", types.SimpleNamespace(Anthropic=FakeAnthropic))
    bridge = build_content_prompt_for_request(_content_request("mint_green"), data_root=Path("data/projects"), prompts_root=Path("/tmp"))

    draft = claude_longform_generator(_content_request("mint_green"), bridge.contract, {})

    assert calls["temperature"] == 0
    assert calls["messages"] == [{"role": "user", "content": bridge.contract.final_prompt}]
    assert draft["title"] == "T"
