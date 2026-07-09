from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from shutil import copytree

from typer.testing import CliRunner

from publishing_gateway.adapters import FacebookAdapter, InstagramAdapter, MockAdapter
from publishing_gateway.approval_verifier import build_approval_signature, verify_approval
from publishing_gateway.brand_guard import validate_brand_display
from publishing_gateway.circuit_breaker import CircuitBreaker
from publishing_gateway.cli import app
from publishing_gateway.contract_validator import validate_contract
from publishing_gateway.exceptions import (
    ERR_APPROVAL_EXPIRED,
    ERR_APPROVAL_INVALID,
    ERR_BRAND_DISPLAY_VIOLATION,
    ERR_DUPLICATE_PUBLISH,
    ERR_PLATFORM_CAPABILITY,
    ERR_PLATFORM_DISABLED,
    PublishingGatewayError,
)
from publishing_gateway.gateway_router import publish_request
from publishing_gateway.platform_capabilities import validate_platform_capability
from publishing_gateway.publisher_queue import PublisherQueue
from publishing_gateway.rate_limit_policy import load_rate_limits
from publishing_gateway.receipt_store import ReceiptStore
from publishing_gateway.renderers import render_receipt_json, render_receipt_markdown
from publishing_gateway.schemas.delivery_receipt import DeliveryReceipt
from publishing_gateway.schemas.publishing_request import Approval, PublishingContent, PublishingRequest
from publishing_gateway.utils.idempotency import ensure_idempotency_key, generate_idempotency_key

runner = CliRunner()
SECRET = "test-secret"


def _config_root(tmp_path: Path) -> Path:
    root = tmp_path / "config" / "projects"
    copytree(Path("config/projects/venho_hotel/publishing"), root / "venho_hotel" / "publishing")
    return root


def _approved_at(minutes_ago: int = 1) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _request(platforms: list[str] | None = None, text: str = "Ven Hồ Hotel bên Hồ Tây", media_type: str = "image") -> PublishingRequest:
    approved_at = _approved_at()
    package_id = "pkg_20260709_westlake"
    return PublishingRequest(
        package_id=package_id,
        project="venho_hotel",
        package_status="approved",
        approval=Approval(
            approved_by="manual_gate",
            approved_at=approved_at,
            approval_signature=build_approval_signature(SECRET, package_id, approved_at),
        ),
        platforms=platforms or ["facebook", "instagram"],
        content=PublishingContent(
            text_prose=text,
            hashtags=["#VenHoHotel", "#HoTay"],
            media_urls=["https://storage.example.test/media/lake.jpg"],
            media_type=media_type,
        ),
    )


def test_schema_contract_accepts_request_and_receipt() -> None:
    request = ensure_idempotency_key(_request())
    receipt = DeliveryReceipt(
        package_id=request.package_id,
        project=request.project,
        overall_status="DRY_RUN",
        published_timestamp="2026-07-09T04:00:05Z",
        idempotency_key=request.idempotency_key or "",
        platform_results={},
        analytics_handoff={"ready_for_m08": True, "tracking_started_at": "2026-07-09T04:00:05Z"},
    )

    assert request.contract_version == "1.0"
    assert request.idempotency_key
    assert receipt.contract_version == "1.0"


def test_approval_verifier_accepts_hmac_and_rejects_bad_or_expired() -> None:
    request = _request()
    assert verify_approval(request, SECRET)

    bad = request.model_copy(update={"approval": request.approval.model_copy(update={"approval_signature": "bad"})})
    try:
        verify_approval(bad, SECRET)
    except PublishingGatewayError as exc:
        assert exc.code == ERR_APPROVAL_INVALID
    else:
        raise AssertionError("bad signature must fail")

    old = _request()
    old_at = _approved_at(minutes_ago=180)
    old = old.model_copy(
        update={
            "approval": old.approval.model_copy(
                update={
                    "approved_at": old_at,
                    "approval_signature": build_approval_signature(SECRET, old.package_id, old_at),
                }
            )
        }
    )
    try:
        verify_approval(old, SECRET)
    except PublishingGatewayError as exc:
        assert exc.code == ERR_APPROVAL_EXPIRED
    else:
        raise AssertionError("expired approval must fail")


def test_contract_validator_checks_enabled_platform_and_url(tmp_path: Path) -> None:
    config_root = _config_root(tmp_path)
    assert validate_contract(_request(), config_root=config_root)

    try:
        validate_contract(_request(platforms=["threads"]), config_root=config_root)
    except PublishingGatewayError as exc:
        assert exc.code == ERR_PLATFORM_DISABLED
    else:
        raise AssertionError("disabled platform must fail")

    bad_url = _request().model_copy(update={"content": _request().content.model_copy(update={"media_urls": ["not-a-url"]})})
    try:
        validate_contract(bad_url, config_root=config_root)
    except PublishingGatewayError as exc:
        assert exc.code != ""
    else:
        raise AssertionError("invalid media URL must fail")


def test_brand_guard_blocks_forbidden_display_name(tmp_path: Path) -> None:
    config_root = _config_root(tmp_path)
    try:
        validate_brand_display(_request(text="Ven Ho Hotel sunset post"), config_root=config_root)
    except PublishingGatewayError as exc:
        assert exc.code == ERR_BRAND_DISPLAY_VIOLATION
    else:
        raise AssertionError("blocked brand display term must fail")


def test_platform_capability_rejects_unsupported_media_type() -> None:
    assert validate_platform_capability(_request(media_type="image"))
    try:
        validate_platform_capability(_request(platforms=["instagram"], media_type="text"))
    except PublishingGatewayError as exc:
        assert exc.code == ERR_PLATFORM_CAPABILITY
    else:
        raise AssertionError("instagram text-only publish must fail in capability check")


def test_idempotency_key_is_deterministic() -> None:
    one = _request()
    two = _request()

    assert generate_idempotency_key(one) == generate_idempotency_key(two)


def test_circuit_breaker_transitions_per_platform() -> None:
    breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=1)
    now = datetime.now(timezone.utc)
    breaker.record_failure("facebook", now=now)
    breaker.record_failure("facebook", now=now)
    assert breaker.allow("facebook", now=now)
    breaker.record_failure("facebook", now=now)
    assert breaker.allow("facebook", now=now) is False
    assert breaker.allow("instagram", now=now) is True
    assert breaker.state_for("facebook", now=now + timedelta(seconds=2)) == "HALF_OPEN"
    breaker.record_success("facebook")
    assert breaker.state_for("facebook") == "CLOSED"


def test_rate_limit_policy_blocks_queue_send(tmp_path: Path) -> None:
    limits = load_rate_limits("venho_hotel", config_root=_config_root(tmp_path))
    queue = PublisherQueue(rate_limits={"facebook": 1})
    queue.enqueue(_request(platforms=["facebook"]), "facebook")
    queue.enqueue(_request(platforms=["facebook"]), "facebook")

    results = queue.run(lambda job: MockAdapter(job.platform).publish(job.request), sent_counts={"facebook": limits["facebook"] - limits["facebook"]})

    assert results["facebook"].error_code is not None


def test_mock_and_core_adapters_build_payloads_offline() -> None:
    request = _request()
    mock = MockAdapter("facebook")
    facebook = FacebookAdapter()
    instagram = InstagramAdapter()

    assert mock.publish(request, dry_run=True).status == "DRY_RUN"
    assert "message" in facebook.build_payload(request)
    assert "caption" in instagram.build_payload(request)


def test_gateway_dry_run_generates_and_stores_receipt(tmp_path: Path) -> None:
    config_root = _config_root(tmp_path)
    data_root = tmp_path / "data" / "projects"
    receipt = publish_request(_request(), SECRET, dry_run=True, data_root=data_root, config_root=config_root)

    assert receipt.overall_status == "DRY_RUN"
    assert receipt.analytics_handoff.ready_for_m08 is True
    assert set(receipt.platform_results) == {"facebook", "instagram"}
    assert ReceiptStore("venho_hotel", data_root=data_root).find_by_package_id(receipt.package_id)


def test_gateway_partial_retry_skips_success_and_retries_failed(tmp_path: Path) -> None:
    config_root = _config_root(tmp_path)
    data_root = tmp_path / "data" / "projects"
    request = ensure_idempotency_key(_request())
    first = publish_request(
        request,
        SECRET,
        dry_run=True,
        data_root=data_root,
        config_root=config_root,
        adapters={"facebook": MockAdapter("facebook"), "instagram": MockAdapter("instagram", fail_platforms=["instagram"])},
    )
    assert first.overall_status == "PARTIAL_SUCCESS"

    second = publish_request(
        request,
        SECRET,
        dry_run=True,
        data_root=data_root,
        config_root=config_root,
        adapters={"facebook": MockAdapter("facebook"), "instagram": MockAdapter("instagram")},
    )

    assert second.platform_results["facebook"].status == "SKIPPED"
    assert second.platform_results["facebook"].error_code == ERR_DUPLICATE_PUBLISH
    assert second.platform_results["instagram"].success is True


def test_duplicate_success_is_not_republished(tmp_path: Path) -> None:
    config_root = _config_root(tmp_path)
    data_root = tmp_path / "data" / "projects"
    request = ensure_idempotency_key(_request(platforms=["facebook"]))
    publish_request(request, SECRET, dry_run=True, data_root=data_root, config_root=config_root, adapters={"facebook": MockAdapter("facebook")})
    second = publish_request(request, SECRET, dry_run=True, data_root=data_root, config_root=config_root, adapters={"facebook": MockAdapter("facebook")})

    assert second.platform_results["facebook"].status == "SKIPPED"
    assert second.platform_results["facebook"].error_code == ERR_DUPLICATE_PUBLISH


def test_receipt_renderers_include_m08_ready_payload(tmp_path: Path) -> None:
    config_root = _config_root(tmp_path)
    receipt = publish_request(_request(platforms=["facebook"]), SECRET, dry_run=True, data_root=tmp_path / "data" / "projects", config_root=config_root, adapters={"facebook": MockAdapter("facebook")})

    assert '"ready_for_m08": true' in render_receipt_json(receipt)
    assert "Delivery Receipt" in render_receipt_markdown(receipt)


def test_publish_cli_dry_run(tmp_path: Path) -> None:
    config_root = _config_root(tmp_path)
    data_root = tmp_path / "data" / "projects"
    request = _request(platforms=["facebook"])
    package_file = tmp_path / "package.json"
    package_file.write_text(request.model_dump_json(indent=2), encoding="utf-8")

    # Keep config local to the test by running from a temporary cwd copy of config.
    result = runner.invoke(
        app,
        [
            "publish",
            "--package-file",
            str(package_file),
            "--approval-secret",
            SECRET,
            "--data-root",
            str(data_root),
            "--config-root",
            str(config_root),
        ],
    )

    assert config_root.exists()
    assert result.exit_code == 0, result.output
    assert "Status: DRY_RUN" in result.output


def test_publish_cli_retry_one_platform(tmp_path: Path) -> None:
    config_root = _config_root(tmp_path)
    data_root = tmp_path / "data" / "projects"
    package_file = tmp_path / "package.json"
    package_file.write_text(_request().model_dump_json(indent=2), encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "retry",
            "--package-file",
            str(package_file),
            "--platform",
            "facebook",
            "--approval-secret",
            SECRET,
            "--data-root",
            str(data_root),
            "--config-root",
            str(config_root),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Retry: facebook" in result.output
