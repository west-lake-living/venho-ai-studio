from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from content_studio.content_engine import ContentEngineResult, generate_content
from content_studio.schemas.content_request import ContentRequest


@dataclass
class CampaignResult:
    message_core: str
    results: List[ContentEngineResult]


def generate_campaign(
    request: ContentRequest,
    channels: List[str],
    *,
    config_root: Path = Path("config/projects"),
    data_root: Path = Path("data/projects"),
    validate: bool = True,
) -> CampaignResult:
    message_core = f"{request.topic} | {request.content_pillar} | {request.cta_type}"
    results: List[ContentEngineResult] = []
    for channel in channels:
        content_type = "tiktok_caption" if channel == "tiktok" else f"{channel}_post"
        channel_request = request.model_copy(
            update={
                "content_type": content_type,
                "topic": request.topic,
                "channels": channels,
            }
        )
        results.append(
            generate_content(
                channel_request,
                config_root=config_root,
                data_root=data_root,
                validate=validate,
            )
        )
    return CampaignResult(message_core=message_core, results=results)

