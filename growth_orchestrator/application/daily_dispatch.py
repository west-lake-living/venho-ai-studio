from __future__ import annotations

from growth_orchestrator.bridges.m07_publishing_bridge import M07PublishingBridge


def daily_dispatch(commands: list[dict]) -> list[dict]:
    return [M07PublishingBridge().dispatch(command) for command in commands]
