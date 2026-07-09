"""Publishing Gateway schema namespace."""

from publishing_gateway.schemas.approval import Approval
from publishing_gateway.schemas.delivery_receipt import DeliveryReceipt
from publishing_gateway.schemas.platform_result import PlatformResult
from publishing_gateway.schemas.publishing_request import PublishingContent, PublishingRequest, PublishingSchedule

__all__ = [
    "Approval",
    "DeliveryReceipt",
    "PlatformResult",
    "PublishingContent",
    "PublishingRequest",
    "PublishingSchedule",
]
