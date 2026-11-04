from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

from growth_engine.domain.kernel.hashing import canonical_json_bytes, sha256_hex


class ChannelPlatform(str, Enum):
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"


@dataclass(frozen=True)
class Channel:
    id: str
    project_id: str
    environment: str
    channel_key: str
    platform: ChannelPlatform
    remote_account_id: str
    name: str
    enabled: bool = False
    paused: bool = False

    def __post_init__(self) -> None:
        for name in ("id", "project_id", "channel_key", "remote_account_id", "name"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} is required")
        if self.environment not in {"test", "production"}:
            raise ValueError("environment must be test or production")
        if not isinstance(self.platform, ChannelPlatform):
            raise ValueError("platform is unsupported")
        if type(self.enabled) is not bool or type(self.paused) is not bool:
            raise ValueError("enabled and paused must be booleans")


@dataclass(frozen=True)
class ChannelConfig:
    id: str
    channel_id: str
    version: int
    make_route_ref: str
    graph_api_version: str
    capability: Mapping[str, object]
    caption_profile: str = "default"

    def __post_init__(self) -> None:
        for name in ("id", "channel_id", "make_route_ref", "graph_api_version", "caption_profile"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} is required")
        if type(self.version) is not int or self.version < 1:
            raise ValueError("version must be a positive integer")
        if not isinstance(self.capability, Mapping):
            raise ValueError("capability must be a mapping")
        object.__setattr__(self, "capability", MappingProxyType(dict(self.capability)))


def config_hash(channel_config: ChannelConfig) -> str:
    """Hash the non-secret immutable routing/capability snapshot."""
    value = {
        "channel_id": channel_config.channel_id,
        "version": channel_config.version,
        "make_route_ref": channel_config.make_route_ref,
        "graph_api_version": channel_config.graph_api_version,
        "capability": dict(channel_config.capability),
        "caption_profile": channel_config.caption_profile,
    }
    return sha256_hex(canonical_json_bytes(value))
