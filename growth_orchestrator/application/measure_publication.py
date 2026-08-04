from __future__ import annotations

from typing import Optional

from growth_orchestrator.bridges.m08_analytics_bridge import M08AnalyticsBridge


def measure_publication(publication_id: str, *, bridge: Optional[M08AnalyticsBridge] = None) -> dict:
    return (bridge or M08AnalyticsBridge()).observe(publication_id)
