from __future__ import annotations

from abc import ABC, abstractmethod

from publishing_gateway.schemas.platform_result import PlatformResult
from publishing_gateway.schemas.publishing_request import PublishingRequest


class BasePlatformAdapter(ABC):
    platform: str

    @abstractmethod
    def build_payload(self, request: PublishingRequest) -> dict:
        raise NotImplementedError

    @abstractmethod
    def publish(self, request: PublishingRequest, dry_run: bool = True) -> PlatformResult:
        raise NotImplementedError
