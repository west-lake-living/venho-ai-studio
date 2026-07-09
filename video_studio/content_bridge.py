from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from content_studio.content_engine import generate_content
from content_studio.schemas.content_request import ContentRequest

from video_studio.schemas.video_package import TextFromContent
from video_studio.schemas.video_request import VideoRequest


@dataclass
class ContentBridgeResult:
    text: TextFromContent
    markdown_path: Path
    json_path: Path


def _content_type_for_platform(platform: str) -> str:
    if platform == "instagram_reels":
        return "instagram_post"
    if platform == "tiktok":
        return "tiktok_caption"
    return "facebook_post"


def build_text_from_content(
    request: VideoRequest,
    *,
    config_root: Path,
    data_root: Path,
) -> ContentBridgeResult:
    content_request = ContentRequest(
        project=request.project,
        content_type=_content_type_for_platform(request.platform),
        topic=request.topic,
        target_audience=request.target_audience,
        content_pillar="Video Studio package support",
        tone="warm, clear, trustworthy",
        target_language=request.caption_language,
        cta_type="booking_soft",
        source_knowledge=[item.model_dump(mode="json") for item in request.source_knowledge],
        validation_required=False,
    )
    result = generate_content(content_request, config_root=config_root, data_root=data_root, validate=False)
    output = result.output
    return ContentBridgeResult(
        text=TextFromContent(
            caption=output.body,
            hook=output.hook,
            voiceover=None,
            cta=output.cta,
            caption_language=request.caption_language,
            source_file=str(result.json_path),
        ),
        markdown_path=result.markdown_path,
        json_path=result.json_path,
    )
