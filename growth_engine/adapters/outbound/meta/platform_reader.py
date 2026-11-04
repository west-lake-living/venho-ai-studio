from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from growth_engine.adapters.outbound.meta.graph_client import GraphClient, MetaErrorKind, MetaGraphError
from growth_engine.domain.channels.channel import ChannelConfig


@dataclass(frozen=True)
class PlatformPostResult:
    existence: str
    ownership: str
    media_present: bool | None = None
    caption_match: bool | None = None
    created_time: str | None = None
    error_kind: str | None = None


class PlatformReader:
    """Read-only Page post reader driven only by P0-verified channel capabilities."""

    def __init__(self, *, access_token: str, transport: Any = None) -> None:
        self._access_token = access_token
        self._transport = transport

    def read_post(
        self,
        *,
        channel_config: ChannelConfig,
        remote_page_id: str,
        platform_post_id: str,
        expected_caption: str,
    ) -> PlatformPostResult:
        capability = channel_config.capability
        fields = _required_fields(capability)
        edge = capability.get("post_collection_edge")
        if not isinstance(edge, str) or not edge.strip() or "REQUIRED_FROM_P0" in edge:
            raise ValueError("verified Meta post collection edge is required in channel capability")
        client = GraphClient(
            api_version=channel_config.graph_api_version,
            access_token=self._access_token,
            collection_edge=edge,
            transport=self._transport,
        )
        try:
            post = client.get_object(platform_post_id, fields)
        except MetaGraphError as error:
            if error.kind is MetaErrorKind.NOT_FOUND:
                return PlatformPostResult("NOT_FOUND", "UNKNOWN", error_kind="NOT_FOUND")
            kind = error.kind.value if error.kind is not None else "UNAVAILABLE"
            return PlatformPostResult("UNAVAILABLE", "UNKNOWN", error_kind=kind)

        post_id = _at_path(post, _required_path(capability, "post_id_path"))
        owner = _at_path(post, _required_path(capability, "owner_page_id_path"))
        caption = _at_path(post, _required_path(capability, "caption_path"))
        created_time = _at_path(post, _required_path(capability, "created_time_path"))
        media_value = _at_path(post, _required_path(capability, "media_path"))
        if not isinstance(post_id, str) or not post_id.strip() or not isinstance(owner, str):
            return PlatformPostResult("UNAVAILABLE", "UNKNOWN", error_kind="INCOMPLETE_RESPONSE")
        if post_id != platform_post_id or owner != remote_page_id:
            return PlatformPostResult("MISMATCH", "MISMATCH")
        if not isinstance(caption, str):
            caption_match = None
        else:
            caption_match = _normalize_caption(caption) == _normalize_caption(expected_caption)
        media_present = bool(media_value) if media_value is not None else None
        return PlatformPostResult(
            "EXISTS",
            "MATCH",
            media_present=media_present,
            caption_match=caption_match,
            created_time=created_time if isinstance(created_time, str) else None,
        )


def _required_fields(capability: Mapping[str, object]) -> tuple[str, ...]:
    value = capability.get("post_fields")
    if not isinstance(value, (list, tuple)) or not value or any(
        not isinstance(field, str) or not field.strip() or "REQUIRED_FROM_P0" in field
        for field in value
    ):
        raise ValueError("verified Meta post fields are required in channel capability")
    return tuple(value)


def _required_path(capability: Mapping[str, object], key: str) -> str:
    value = capability.get(key)
    if not isinstance(value, str) or not value.strip() or "REQUIRED_FROM_P0" in value:
        raise ValueError(f"verified Meta capability {key} is required")
    return value


def _at_path(payload: Mapping[str, Any], path: str) -> object | None:
    current: object = payload
    for part in path.split("."):
        if not isinstance(current, Mapping):
            return None
        current = current.get(part)
    return current


def _normalize_caption(value: str) -> str:
    return "\n".join(line.rstrip() for line in value.replace("\r\n", "\n").replace("\r", "\n").split("\n"))
