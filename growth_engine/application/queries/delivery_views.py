from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol

from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.revision import DeliveryRevision
from growth_engine.domain.media.asset import MediaVariant


@dataclass(frozen=True)
class ReviewSnapshotData:
    delivery: Delivery
    revision: DeliveryRevision | None
    channel_key: str
    channel_name: str
    remote_account_id: str
    scheduled_at_ms: int | None
    deadline_at_ms: int | None
    variant: MediaVariant | None
    action_context: Mapping[str, object]
    image_label: str | None = None


class ReviewDataReader(Protocol):
    def load_review_data(self, delivery_id: str) -> ReviewSnapshotData | None: ...
