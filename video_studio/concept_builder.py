from __future__ import annotations

from video_studio.schemas.video_package import Concept
from video_studio.schemas.video_request import VideoRequest


def build_concept(request: VideoRequest, config: dict) -> Concept:
    style = config.get("video_style", {})
    tone = style.get("default_tone", "warm, natural, realistic")
    title = request.topic.title()
    return Concept(
        title=title,
        objective=f"Create a {request.duration_seconds}s {request.platform} video package for {request.topic}.",
        tone=tone,
    )

