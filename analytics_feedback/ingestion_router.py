from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from analytics_feedback.collection_scheduler import CollectionTask, build_collection_tasks
from analytics_feedback.schemas.delivery_receipt_ref import DeliveryReceiptRef, PlatformReceiptRef


def load_delivery_receipt(path: Path) -> DeliveryReceiptRef:
    data = json.loads(path.read_text(encoding="utf-8"))
    return parse_delivery_receipt(data)


def parse_delivery_receipt(data: Dict[str, Any]) -> DeliveryReceiptRef:
    platform_results = {
        platform: PlatformReceiptRef(**result)
        for platform, result in data.get("platform_results", {}).items()
    }
    return DeliveryReceiptRef(
        package_id=data["package_id"],
        project=data["project"],
        published_timestamp=data["published_timestamp"],
        content_type=data.get("content_type", data.get("metadata", {}).get("content_type", "unknown")),
        pillar=data.get("pillar", data.get("metadata", {}).get("pillar", "unknown")),
        theme=data.get("theme", data.get("metadata", {}).get("theme")),
        platform_results=platform_results,
    )


def route_receipt(path: Path) -> List[CollectionTask]:
    return build_collection_tasks(load_delivery_receipt(path))
