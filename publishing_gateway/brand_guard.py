from __future__ import annotations

from pathlib import Path

import yaml

from publishing_gateway.exceptions import ERR_BRAND_DISPLAY_VIOLATION, PublishingGatewayError
from publishing_gateway.schemas.publishing_request import PublishingRequest


def validate_brand_display(request: PublishingRequest, config_root: Path = Path("config/projects")) -> bool:
    path = config_root / request.project / "publishing" / "brand_display_rules.yaml"
    config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    text = " ".join([request.content.text_prose, " ".join(request.content.hashtags)])
    for blocked in config.get("blocked_display_terms", []):
        if blocked and blocked in text:
            raise PublishingGatewayError(f"blocked display term found: {blocked}", ERR_BRAND_DISPLAY_VIOLATION)
    if config.get("require_display_name", False):
        required_names = config.get("required_display_name", [])
        if required_names and not any(name in text for name in required_names):
            raise PublishingGatewayError("required display name missing", ERR_BRAND_DISPLAY_VIOLATION)
    return True
