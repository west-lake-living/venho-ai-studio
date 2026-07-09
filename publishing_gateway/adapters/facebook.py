from __future__ import annotations

from publishing_gateway.adapters.base_adapter import BasePlatformAdapter
from publishing_gateway.exceptions import ERR_ADAPTER_FAILED
from publishing_gateway.schemas.platform_result import PlatformResult
from publishing_gateway.schemas.publishing_request import PublishingRequest


class FacebookAdapter(BasePlatformAdapter):
    platform = "facebook"

    def build_payload(self, request: PublishingRequest) -> dict:
        return {
            "message": request.content.text_prose,
            "attached_media": request.content.media_urls,
            "media_type": request.content.media_type,
        }

    def publish(self, request: PublishingRequest, dry_run: bool = True) -> PlatformResult:
        payload = self.build_payload(request)
        if dry_run:
            return PlatformResult(platform=self.platform, success=True, status="DRY_RUN", payload=payload)
        return PlatformResult(platform=self.platform, success=False, status="FAILED", error_code=ERR_ADAPTER_FAILED, error_message="real Facebook API publishing requires controlled manual test", payload=payload)
