from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from growth_engine.adapters.inbound.api.app import create_app
from growth_engine.adapters.inbound.api.auth import Principal, require_scopes
from growth_engine.adapters.inbound.cli.main import app as cli_app
from growth_engine.application.errors import NotFound
from growth_engine.bootstrap import build_container
from growth_engine.domain.kernel.errors import DomainError, ErrorCode
from growth_engine.settings import Settings


def _app(tmp_path: Path, *, principal: str = "bff", token: str = "synthetic-bearer") -> FastAPI:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    settings = Settings(
        env="test",
        db_path=str(tmp_path / "growth.db"),
        media_root=str(tmp_path / "media"),
        public_base_url="http://localhost:8021",
        service_tokens=f"{principal}:{token_hash}",
    )
    return create_app(build_container(settings))


def _add_protected_route(app: FastAPI) -> None:
    @app.get("/api/test/protected")
    def protected(principal: Principal = Depends(require_scopes("dashboard:read"))) -> dict[str, str]:
        return {"principal": principal.id}

    @app.get("/api/test/domain-error")
    def domain_error() -> None:
        raise DomainError(
            ErrorCode.REVISION_CONFLICT,
            "Nội dung hoặc ảnh đã thay đổi; hãy mở lại bản xem trước.",
            {"field": "caption", "secret": "do-not-return", "nested": {"token": "do-not-return"}},
        )

    @app.get("/api/test/application-error")
    def application_error() -> None:
        raise NotFound("Không tìm thấy dữ liệu.")


def test_missing_bearer_returns_401_json_and_scope_mismatch_returns_403(tmp_path: Path) -> None:
    app = _app(tmp_path)
    _add_protected_route(app)
    client = TestClient(app)

    missing = client.get("/api/test/protected")
    assert missing.status_code == 401
    assert missing.headers["content-type"].startswith("application/json")
    assert missing.json()["error"]["code"] == "ERR_GC2_UNAUTHENTICATED"
    assert "Phiên đăng nhập không hợp lệ" in missing.json()["error"]["message"]

    authenticated = client.get(
        "/api/test/protected", headers={"Authorization": "Bearer synthetic-bearer"}
    )
    assert authenticated.status_code == 200
    assert authenticated.json() == {"principal": "bff"}
    assert authenticated.headers["cache-control"] == "no-store"
    assert authenticated.headers["x-correlation-id"]

    make_app = _app(tmp_path / "make", principal="make-fb-hanoi")
    _add_protected_route(make_app)
    token = "synthetic-bearer"
    forbidden = TestClient(make_app).get(
        "/api/test/protected", headers={"Authorization": f"Bearer {token}"}
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "ERR_GC2_FORBIDDEN"


def test_ready_returns_503_when_sqlite_cannot_open(tmp_path: Path) -> None:
    settings = Settings(
        env="test",
        db_path=str(tmp_path / "missing-parent" / "growth.db"),
        media_root=str(tmp_path / "media"),
        public_base_url="http://localhost:8021",
        service_tokens="bff:" + hashlib.sha256(b"synthetic-bearer").hexdigest(),
    )
    response = TestClient(create_app(build_container(settings))).get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}


def test_domain_and_application_errors_follow_api_contract(tmp_path: Path) -> None:
    app = _app(tmp_path)
    _add_protected_route(app)
    client = TestClient(app)

    domain = client.get("/api/test/domain-error")
    assert domain.status_code == 412
    assert domain.json()["error"]["code"] == "ERR_GC2_REVISION_CONFLICT"
    assert domain.json()["error"]["message"] == "Nội dung hoặc ảnh đã thay đổi; hãy mở lại bản xem trước."
    assert domain.json()["error"]["retryable"] is False
    assert domain.json()["error"]["correlation_id"]
    assert domain.json()["error"]["details"] == {"field": "caption", "nested": {}}
    assert domain.headers["cache-control"] == "no-store"

    application = client.get("/api/test/application-error")
    assert application.status_code == 404
    assert application.json()["error"]["code"] == "ERR_GC2_NOT_FOUND"


def test_api_json_body_limit_returns_contract_error(tmp_path: Path) -> None:
    app = _app(tmp_path)
    response = TestClient(app).post(
        "/api/test/protected",
        content=b"x" * (64 * 1024 + 1),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "ERR_GC2_PAYLOAD_TOO_LARGE"
    assert response.headers["cache-control"] == "no-store"


def test_composition_root_wires_migrator_and_ready_health(tmp_path: Path) -> None:
    settings = Settings(
        env="test",
        db_path=str(tmp_path / "growth.db"),
        media_root=str(tmp_path / "media"),
        public_base_url="http://localhost:8021",
        service_tokens="bff:" + hashlib.sha256(b"synthetic-bearer").hexdigest(),
    )
    container = build_container(settings)
    result = container.migration_service.run(Path(settings.db_path), check=False)
    assert "schema version 9" in result
    response = TestClient(create_app(container)).get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "schema_version": 9}
    report = container.doctor_service.run()
    assert "Python & SQLite version" in report.render()
    assert "Heartbeat age" in report.render()


def test_doctor_cli_prints_pass_warn_fail_table(tmp_path: Path) -> None:
    database = tmp_path / "growth.db"
    media = tmp_path / "media"
    media.mkdir()
    token_hash = hashlib.sha256(b"synthetic-bearer").hexdigest()
    settings = Settings(
        env="test",
        db_path=str(database),
        media_root=str(media),
        public_base_url="http://localhost:8021",
        capability_keys="test-kid:synthetic-key",
        service_tokens=f"bff:{token_hash}",
        make_webhook_urls={"TEST": "https://example.test/hook"},
        meta_read_tokens={"TEST": "synthetic-read-token"},
        telegram={"BOT_TOKEN": "synthetic-token", "CHAT_ID": "synthetic-chat"},
    )
    build_container(settings).migration_service.run(database, check=False)
    environment = {
        "GE_ENV": "test",
        "GE_DB_PATH": str(database),
        "GE_MEDIA_ROOT": str(media),
        "GE_PUBLIC_BASE_URL": "http://localhost:8021",
        "GE_CAPABILITY_KEYS": "test-kid:synthetic-key",
        "GE_SERVICE_TOKENS": f"bff:{token_hash}",
        "GE_MAKE_WEBHOOK_URL_TEST": "https://example.test/hook",
        "GE_META_READ_TOKEN_TEST": "synthetic-read-token",
        "GE_TELEGRAM_BOT_TOKEN": "synthetic-token",
        "GE_TELEGRAM_CHAT_ID": "synthetic-chat",
    }
    result = CliRunner().invoke(cli_app, ["doctor", "--pre-switch"], env=environment)
    assert result.exit_code == 0, result.output
    assert "**PASS**" in result.output
    assert "**WARN**" in result.output
    assert "--pre-switch" in result.output


def test_migrate_cli_uses_composition_root_by_default(tmp_path: Path) -> None:
    database = tmp_path / "growth.db"
    result = CliRunner().invoke(
        cli_app,
        ["migrate"],
        env={"GE_ENV": "test", "GE_DB_PATH": str(database)},
    )
    assert result.exit_code == 0, result.output
    assert "Applied 8 migration(s); schema version 9" in result.output

    checked = CliRunner().invoke(
        cli_app,
        ["migrate", "--check"],
        env={"GE_ENV": "test", "GE_DB_PATH": str(database)},
    )
    assert checked.exit_code == 0, checked.output
    assert "Schema is current at version 9" in checked.output


def test_non_bff_cannot_supply_venho_actor_header(tmp_path: Path) -> None:
    app = _app(tmp_path, principal="make-fb-hanoi")
    _add_protected_route(app)
    response = TestClient(app).get(
        "/api/test/protected",
        headers={"Authorization": "Bearer synthetic-bearer", "X-Venho-Actor": "operator"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ERR_GC2_FORBIDDEN"
