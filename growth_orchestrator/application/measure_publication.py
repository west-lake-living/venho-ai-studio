from __future__ import annotations

from growth_orchestrator.bridges.m08_analytics_bridge import M08AnalyticsBridge


def measure_publication(publication_id: str) -> dict:
    return M08AnalyticsBridge().observe(publication_id)
