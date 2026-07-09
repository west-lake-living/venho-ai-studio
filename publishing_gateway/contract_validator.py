from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable

import yaml

from publishing_gateway.exceptions import ERR_CONTRACT_INVALID, ERR_PLATFORM_DISABLED, PublishingGatewayError
from publishing_gateway.schemas.publishing_request import PublishingRequest
from publishing_gateway.utils.url_checker import is_valid_media_url


def load_platform_config(project: str, config_root: Path = Path("config/projects")) -> Dict[str, object]:
    path = config_root / project / "publishing" / "platforms.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def validate_contract(request: PublishingRequest, config_root: Path = Path("config/projects")) -> bool:
    if request.contract_version != "1.0":
        raise PublishingGatewayError("unsupported publishing contract version", ERR_CONTRACT_INVALID)
    if not request.content.text_prose.strip():
        raise PublishingGatewayError("content.text_prose is required", ERR_CONTRACT_INVALID)
    for media_url in request.content.media_urls:
        if not is_valid_media_url(media_url):
            raise PublishingGatewayError(f"invalid media url: {media_url}", ERR_CONTRACT_INVALID)

    config = load_platform_config(request.project, config_root=config_root)
    platforms = config.get("platforms", {})
    for platform in _unique(request.platforms):
        platform_config = platforms.get(platform)
        if not platform_config:
            raise PublishingGatewayError(f"platform not configured: {platform}", ERR_PLATFORM_DISABLED)
        if not platform_config.get("enabled", False):
            raise PublishingGatewayError(f"platform disabled: {platform}", ERR_PLATFORM_DISABLED)
    return True


def _unique(values: Iterable[str]) -> Iterable[str]:
    seen = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            yield value
