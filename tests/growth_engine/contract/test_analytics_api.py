from __future__ import annotations

# _synthetic: true — cần thay bằng fixture thật từ P0-T03/P0-T04.

import hashlib
from pathlib import Path

from fastapi.testclient import TestClient

from growth_engine.adapters.inbound.api.app import create_app
from growth_engine.bootstrap import build_container
from growth_engine.settings import Settings


def _app(tmp_path: Path):
    token = "synthetic-dashboard-bearer"
    settings = Settings(
        env="test",
        db_path=str(tmp_path / "growth.db"),
        media_root=str(tmp_path / "media"),
        public_base_url="https://growth.example.invalid",
        service_tokens="bff:" + hashlib.sha256(token.encode()).hexdigest(),
    )
    container = build_container(settings)

    class AnalyticsStub:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str]] = []

        def weekly(self, *, week_start: str, checkpoint: str):
            self.calls.append((week_start, checkpoint))
            if week_start != "2026-11-02" or checkpoint not in {"24h", "72h", "7d"}:
                raise ValueError("invalid weekly analytics query")
            return {"week_start": week_start, "checkpoint": checkpoint, "source": "meta_graph", "groups": []}

    service = AnalyticsStub()
    object.__setattr__(container, "analytics_views", service)
    return TestClient(create_app(container)), service


def test_weekly_analytics_requires_dashboard_read_and_is_not_cached(tmp_path: Path) -> None:
    client, service = _app(tmp_path)

    unauthorized = client.get("/api/growth/v2/analytics/weekly?week_start=2026-11-02")
    assert unauthorized.status_code == 401

    response = client.get(
        "/api/growth/v2/analytics/weekly?week_start=2026-11-02&checkpoint=7d",
        headers={"Authorization": "Bearer synthetic-dashboard-bearer"},
    )
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["source"] == "meta_graph"
    assert service.calls == [("2026-11-02", "7d")]


def test_weekly_analytics_validation_is_returned_as_422(tmp_path: Path) -> None:
    client, _service = _app(tmp_path)
    response = client.get(
        "/api/growth/v2/analytics/weekly?week_start=2026-11-03&checkpoint=adhoc",
        headers={"Authorization": "Bearer synthetic-dashboard-bearer"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ERR_GC2_VALIDATION"
