from __future__ import annotations

from collections.abc import Mapping


CAPABILITY_STATES = frozenset({"BLOCKED", "SUPPORTED"})


def capability_state(
    registry: Mapping[str, object], capability: str, channel_key: str
) -> str:
    """Resolve an opt-in metric capability; absent or invalid config is safely BLOCKED."""
    capabilities = registry.get("capabilities")
    capability_config = capabilities.get(capability) if isinstance(capabilities, Mapping) else None
    if not isinstance(capability_config, Mapping):
        return "BLOCKED"
    channel_overrides = capability_config.get("channels")
    channel_value = channel_overrides.get(channel_key) if isinstance(channel_overrides, Mapping) else None
    value = channel_value if channel_value is not None else capability_config.get("default", "BLOCKED")
    state = str(value).strip().upper()
    return state if state in CAPABILITY_STATES else "BLOCKED"
