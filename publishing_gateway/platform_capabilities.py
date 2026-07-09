from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Set

from publishing_gateway.exceptions import ERR_PLATFORM_CAPABILITY, PublishingGatewayError
from publishing_gateway.schemas.publishing_request import PublishingRequest


@dataclass(frozen=True)
class PlatformCapability:
    media_types: Set[str]
    max_text_chars: int
    max_media_count: int


DEFAULT_CAPABILITIES: Dict[str, PlatformCapability] = {
    "facebook": PlatformCapability({"text", "image", "carousel", "video", "reel"}, 63206, 10),
    "instagram": PlatformCapability({"image", "carousel", "video", "reel"}, 2200, 10),
    "threads": PlatformCapability({"text", "image"}, 500, 1),
    "google_business": PlatformCapability({"text", "image"}, 1500, 1),
}


def validate_platform_capability(request: PublishingRequest, capabilities: Dict[str, PlatformCapability] = DEFAULT_CAPABILITIES) -> bool:
    media_count = len(request.content.media_urls)
    text_len = len(request.content.text_prose)
    for platform in request.platforms:
        capability = capabilities.get(platform)
        if not capability:
            raise PublishingGatewayError(f"unknown platform capability: {platform}", ERR_PLATFORM_CAPABILITY)
        if request.content.media_type not in capability.media_types:
            raise PublishingGatewayError(f"{platform} does not support {request.content.media_type}", ERR_PLATFORM_CAPABILITY)
        if text_len > capability.max_text_chars:
            raise PublishingGatewayError(f"{platform} text exceeds capability", ERR_PLATFORM_CAPABILITY)
        if media_count > capability.max_media_count:
            raise PublishingGatewayError(f"{platform} media count exceeds capability", ERR_PLATFORM_CAPABILITY)
    return True
