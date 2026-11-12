from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from growth_engine.application.errors import Conflict, NotFound
from growth_engine.application.queries.delivery_views import ReviewDataReader
from growth_engine.domain.delivery.allowed_actions import allowed_actions


@dataclass(frozen=True)
class ReviewSnapshot:
    delivery_id: str
    state: str
    row_version: int
    etag: str
    channel_key: str
    channel_name: str
    remote_account_id: str
    revision_id: str | None
    payload_hash: str | None
    caption: str | None
    scheduled_at_ms: int | None
    deadline_at_ms: int | None
    preview_url: str | None
    preview_sha256: str | None
    image_label: str | None
    allowed_actions: tuple[dict[str, object], ...]


class BuildReviewSnapshot:
    def __init__(
        self,
        reader: ReviewDataReader,
        *,
        preview_url_builder: Callable[[str], str],
    ) -> None:
        self._reader = reader
        self._preview_url_builder = preview_url_builder

    def execute(self, delivery_id: str) -> ReviewSnapshot:
        data = self._reader.load_review_data(delivery_id)
        if data is None:
            raise NotFound("Không tìm thấy bài cần duyệt.")
        if (data.revision is None) != (data.variant is None):
            raise Conflict("Revision và biến thể ảnh không đồng nhất.")

        preview_url = None
        preview_sha256 = None
        revision_id = None
        payload_hash = None
        caption = None
        if data.revision is not None and data.variant is not None:
            payload = data.revision.payload
            media = payload.get("media")
            if not isinstance(media, list) or not media or not isinstance(media[0], dict):
                raise Conflict("Revision không có artifact ảnh hợp lệ.")
            expected_sha256 = media[0].get("sha256")
            if expected_sha256 != data.variant.sha256:
                raise Conflict("Preview không khớp artifact trong revision.")
            caption_value = payload.get("caption")
            if not isinstance(caption_value, str):
                raise Conflict("Revision không có caption hợp lệ.")
            preview_sha256 = data.variant.sha256
            preview_url = self._preview_url_builder(preview_sha256)
            revision_id = str(payload.get("revision_id"))
            payload_hash = data.revision.payload_hash
            caption = caption_value

        actions = tuple(
            {
                "action": item.action,
                "enabled": item.enabled,
                "reason_code": item.reason_code,
            }
            for item in allowed_actions(data.delivery, data.action_context)
        )
        return ReviewSnapshot(
            delivery_id=data.delivery.id,
            state=data.delivery.state.value,
            row_version=data.delivery.row_version,
            etag=f'"delivery:{data.delivery.id}:{data.delivery.row_version}"',
            channel_key=data.channel_key,
            channel_name=data.channel_name,
            remote_account_id=data.remote_account_id,
            revision_id=revision_id,
            payload_hash=payload_hash,
            caption=caption,
            scheduled_at_ms=data.scheduled_at_ms,
            deadline_at_ms=data.deadline_at_ms,
            preview_url=preview_url,
            preview_sha256=preview_sha256,
            image_label=data.image_label,
            allowed_actions=actions,
        )


def build_review_snapshot(use_case: BuildReviewSnapshot, delivery_id: str) -> ReviewSnapshot:
    return use_case.execute(delivery_id)
