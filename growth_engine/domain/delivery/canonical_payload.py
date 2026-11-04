from __future__ import annotations

from collections.abc import Mapping, Sequence

from growth_engine.domain.kernel.hashing import canonical_json_bytes, sha256_hex


_MEDIA_FIELDS = {"sha256", "mime", "width", "height"}


def build_publish_payload(
    *,
    delivery_id: str,
    revision_id: str,
    channel_id: str,
    remote_account_id: str,
    channel_config_hash: str,
    caption: str,
    media: Sequence[Mapping[str, object]],
    scheduled_at_ms: int,
    deadline_at_ms: int,
    qc_report_id: str,
    ruleset_hash: str,
    fact_snapshot_hash: str,
    schema_version: str = "growth.publish.v2",
) -> tuple[dict[str, object], bytes, str]:
    """Build a canonical payload from already-normalized revision inputs."""
    if not isinstance(caption, str):
        raise ValueError("caption must be a string")
    if schema_version != "growth.publish.v2":
        raise ValueError("schema_version must be growth.publish.v2")
    scheduled_at_ms = _require_int("scheduled_at_ms", scheduled_at_ms)
    deadline_at_ms = _require_int("deadline_at_ms", deadline_at_ms)
    if scheduled_at_ms < 0 or deadline_at_ms < scheduled_at_ms:
        raise ValueError("deadline_at_ms must be greater than or equal to scheduled_at_ms")

    media_payload: list[dict[str, object]] = []
    for item in media:
        if not isinstance(item, Mapping) or set(item) != _MEDIA_FIELDS:
            raise ValueError("each media item must contain sha256, mime, width, and height")
        width = _require_int("width", item["width"])
        height = _require_int("height", item["height"])
        media_payload.append(
            {
                "sha256": item["sha256"],
                "mime": item["mime"],
                "width": width,
                "height": height,
            }
        )
    if not media_payload:
        raise ValueError("media must contain at least one item")

    payload: dict[str, object] = {
        "schema_version": schema_version,
        "delivery_id": delivery_id,
        "revision_id": revision_id,
        "channel_id": channel_id,
        "remote_account_id": remote_account_id,
        "channel_config_hash": channel_config_hash,
        "caption": caption,
        "media": media_payload,
        "scheduled_at_ms": scheduled_at_ms,
        "deadline_at_ms": deadline_at_ms,
        "qc_report_id": qc_report_id,
        "ruleset_hash": ruleset_hash,
        "fact_snapshot_hash": fact_snapshot_hash,
    }
    canonical_bytes = canonical_json_bytes(payload)
    return payload, canonical_bytes, sha256_hex(canonical_bytes)


def _require_int(name: str, value: object) -> int:
    if type(value) is not int:
        raise ValueError(f"{name} must be an integer")
    return value
