from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from analytics_feedback.schemas.delivery_receipt_ref import DeliveryReceiptRef
from analytics_feedback.utils.time_windows import add_window


DEFAULT_WINDOWS = ["24h", "72h", "7d", "14d"]


@dataclass(frozen=True)
class CollectionTask:
    package_id: str
    project: str
    platform: str
    post_id: str
    snapshot_timestamp_utc: str
    window: str


def build_collection_tasks(receipt: DeliveryReceiptRef, windows: Iterable[str] = DEFAULT_WINDOWS) -> List[CollectionTask]:
    tasks: List[CollectionTask] = []
    seen = set()
    for platform, result in receipt.platform_results.items():
        if not result.success or result.status not in {"PUBLISHED", "DRY_RUN"} or not result.post_id:
            continue
        for window in windows:
            timestamp = add_window(receipt.published_timestamp, window)
            key = (receipt.package_id, platform, timestamp)
            if key in seen:
                continue
            seen.add(key)
            tasks.append(
                CollectionTask(
                    package_id=receipt.package_id,
                    project=receipt.project,
                    platform=platform,
                    post_id=result.post_id,
                    snapshot_timestamp_utc=timestamp,
                    window=window,
                )
            )
    return tasks
