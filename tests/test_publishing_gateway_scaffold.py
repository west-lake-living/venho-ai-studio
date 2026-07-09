from __future__ import annotations

import importlib
from pathlib import Path

import yaml

from publishing_gateway.exceptions import (
    ERR_APPROVAL_INVALID,
    ERR_BRAND_DISPLAY_VIOLATION,
    ERR_DUPLICATE_PUBLISH,
    PublishingGatewayError,
)


def test_publishing_gateway_imports() -> None:
    module = importlib.import_module("publishing_gateway")

    assert module.MODULE_ID == "M07"
    assert module.CONTRACT_VERSION == "1.0"


def test_publishing_gateway_scaffold_directories_exist() -> None:
    root = Path("publishing_gateway")
    expected = {"adapters", "schemas", "utils", "renderers"}

    assert expected <= {path.name for path in root.iterdir() if path.is_dir()}
    assert (root / "README.md").exists()
    assert (root / "exceptions.py").exists()


def test_publishing_config_scaffold_matches_mvp_platform_scope() -> None:
    config_dir = Path("config/projects/venho_hotel/publishing")
    platforms = yaml.safe_load((config_dir / "platforms.yaml").read_text(encoding="utf-8"))

    assert platforms["project"] == "venho_hotel"
    assert platforms["platforms"]["facebook"]["enabled"] is True
    assert platforms["platforms"]["instagram"]["enabled"] is True
    assert platforms["platforms"]["threads"]["enabled"] is False
    assert platforms["platforms"]["google_business"]["enabled"] is False


def test_publishing_gateway_error_codes_are_stable() -> None:
    err = PublishingGatewayError("approval failed", code=ERR_APPROVAL_INVALID)

    assert str(err) == "ERR_APPROVAL_INVALID: approval failed"
    assert ERR_APPROVAL_INVALID in PublishingGatewayError.known_codes
    assert ERR_BRAND_DISPLAY_VIOLATION in PublishingGatewayError.known_codes
    assert ERR_DUPLICATE_PUBLISH in PublishingGatewayError.known_codes
