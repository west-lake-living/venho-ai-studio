from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AiStudioCapability:
    id: str
    module: str
    requires_approval: bool
    can_execute: bool
    can_publish: bool


CAPABILITIES = {
    "wardrobe_ingest": AiStudioCapability("wardrobe_ingest", "M04", True, True, False),
    "content_generate": AiStudioCapability("content_generate", "M05", False, True, False),
    "video_package": AiStudioCapability("video_package", "M06", False, True, False),
    "publish_content": AiStudioCapability("publish_content", "M07", True, True, True),
}


def list_capabilities() -> list[AiStudioCapability]:
    return [CAPABILITIES[key] for key in sorted(CAPABILITIES)]


def get_capability(capability_id: str) -> AiStudioCapability:
    try:
        return CAPABILITIES[capability_id]
    except KeyError as exc:
        raise ValueError(f"Unknown AiStudioPort capability: {capability_id}") from exc
