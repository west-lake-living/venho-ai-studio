from __future__ import annotations

from typing import Iterable, Set

from publishing_gateway.adapters.base_adapter import BasePlatformAdapter
from publishing_gateway.exceptions import ERR_ADAPTER_FAILED
from publishing_gateway.schemas.platform_result import PlatformResult
from publishing_gateway.schemas.publishing_request import PublishingRequest


class MockAdapter(BasePlatformAdapter):
    def __init__(self, platform: str, fail_platforms: Iterable[str] = ()) -> None:
        self.platform = platform
        self.fail_platforms: Set[str] = set(fail_platforms)

    def build_payload(self, request: PublishingRequest) -> dict:
        return {
            "platform": self.platform,
            "text": request.content.text_prose,
            "hashtags": request.content.hashtags,
            "media_urls": request.content.media_urls,
            "media_type": request.content.media_type,
        }

    def publish(self, request: PublishingRequest, dry_run: bool = True) -> PlatformResult:
        payload = self.build_payload(request)
        if self.platform in self.fail_platforms:
            return PlatformResult(
                platform=self.platform,
                success=False,
                status="FAILED",
                error_code=ERR_ADAPTER_FAILED,
                error_message="mock adapter configured failure",
                payload=payload,
            )
        status = "DRY_RUN" if dry_run else "PUBLISHED"
        return PlatformResult(
            platform=self.platform,
            success=True,
            status=status,
            post_id=f"mock_{self.platform}_{request.package_id}",
            public_url=f"https://example.test/{self.platform}/{request.package_id}",
            payload=payload,
        )
