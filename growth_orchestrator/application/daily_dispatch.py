from __future__ import annotations

from growth_orchestrator.bridges.m07_publishing_bridge import M07PublishingBridge


def daily_dispatch(commands: list[dict], *, bridge: M07PublishingBridge | None = None) -> list[dict]:
    bridge = bridge or M07PublishingBridge()
    return [bridge.dispatch(command) for command in commands]
