from __future__ import annotations

from video_studio.schemas.video_request import VideoRequest
from video_studio.video_engine import VideoEngineResult, generate_video_package


def build_character_video(request: VideoRequest, **kwargs) -> VideoEngineResult:
    return generate_video_package(request.model_copy(update={"video_type": "character", "include_character": True}), **kwargs)

