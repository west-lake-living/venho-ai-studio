from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from growth_engine.adapters.inbound.api.app import create_app
from growth_engine.bootstrap import build_container
from growth_engine.domain.kernel.errors import DomainError, ErrorCode
from growth_engine.settings import Settings


class DashboardStub:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.fail_operation: str | None = None
        self.result: object = {"operation": "ok", "data": {"safe": True}}

    def execute(self, operation: str, **kwargs: object) -> object:
        self.calls.append((operation, kwargs))
        if self.fail_operation == operation:
            if operation == "delivery.revision.create":
                raise DomainError(ErrorCode.REVISION_CONFLICT, "stale")
            if operation == "approval.batch":
                raise DomainError(ErrorCode.STATE_CONFLICT, "batch conflict", {"conflicts": ["d-2"]})
            raise DomainError(ErrorCode.DB_BUSY, "database unavailable")
        return self.result


def _app(tmp_path: Path) -> tuple[FastAPI, DashboardStub]:
    token = "synthetic-dashboard-bearer"
    settings = Settings(
        env="test",
        db_path=str(tmp_path / "growth.db"),
        media_root=str(tmp_path / "media"),
        public_base_url="http://localhost:8021",
        service_tokens="bff:" + hashlib.sha256(token.encode()).hexdigest(),
    )
    container = build_container(settings)
    dashboard = DashboardStub()
    object.__setattr__(container, "dashboard_api", dashboard)
    return create_app(container), dashboard


def _headers() -> dict[str, str]:
    return {"Authorization": "Bearer synthetic-dashboard-bearer"}


def test_dashboard_routes_fail_closed_when_dashboard_service_is_not_composed(tmp_path: Path) -> None:
    token = "synthetic-dashboard-bearer"
    settings = Settings(
        env="test",
        db_path=str(tmp_path / "growth.db"),
        media_root=str(tmp_path / "media"),
        public_base_url="http://localhost:8021",
        service_tokens="bff:" + hashlib.sha256(token.encode()).hexdigest(),
    )
    response = TestClient(create_app(build_container(settings))).get(
        "/api/growth/v2/channels", headers=_headers()
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ERR_GC2_DEPENDENCY_UNAVAILABLE"


def test_stale_revision_returns_412_and_preserves_if_match(tmp_path: Path) -> None:
    app, service = _app(tmp_path)
    service.fail_operation = "delivery.revision.create"
    response = TestClient(app).post(
        "/api/growth/v2/deliveries/d-1/revisions",
        json={"caption": "updated"},
        headers={**_headers(), "If-Match": '"delivery:d-1:7"', "Idempotency-Key": "test-1"},
    )
    assert response.status_code == 412
    assert service.calls[-1][1]["if_match"] == '"delivery:d-1:7"'


def test_batch_conflict_returns_409_with_conflict_ids(tmp_path: Path) -> None:
    app, service = _app(tmp_path)
    service.fail_operation = "approval.batch"
    response = TestClient(app).post(
        "/api/growth/v2/approvals/batch",
        json={"items": [{"delivery_id": "d-1"}]},
        headers={**_headers(), "Idempotency-Key": "test-batch"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["details"] == {"conflicts": ["d-2"]}


def test_database_failure_is_503_and_response_never_exposes_make_credentials(tmp_path: Path) -> None:
    app, service = _app(tmp_path)
    service.fail_operation = "deliveries.list"
    response = TestClient(app).get("/api/growth/v2/deliveries", headers=_headers())
    assert response.status_code == 503
    assert "make.com" not in response.text.casefold()
    assert "token" not in response.text.casefold()


def test_response_strips_credentials_and_make_webhook_urls(tmp_path: Path) -> None:
    app, service = _app(tmp_path)
    service.result = {
        "delivery_id": "d-1",
        "row_version": 4,
        "token": "synthetic-secret",
        "webhook_url": "https://hook.make.com/private-value",
        "title": "safe",
    }
    response = TestClient(app).get("/api/growth/v2/deliveries/d-1/review", headers=_headers())
    assert response.status_code == 200
    assert response.headers["etag"] == '"delivery:d-1:4"'
    assert response.json() == {"delivery_id": "d-1", "row_version": 4, "title": "safe"}
