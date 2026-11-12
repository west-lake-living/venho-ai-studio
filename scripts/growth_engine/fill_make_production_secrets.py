#!/usr/bin/env python3
"""Fill the production Make draft from the protected bearer handoff."""

from __future__ import annotations

import argparse
import getpass
import json
import stat
import sys
from pathlib import Path
from typing import Any

try:
    from scripts.growth_engine import fill_make_test_secrets as shared
except ModuleNotFoundError as error:
    if error.name != "scripts":
        raise
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.growth_engine import fill_make_test_secrets as shared


PRODUCTION_BASE_URL = "https://growth-api.venhohotel.com"
BLUEPRINT_PATH = Path("_incoming/make_production_import.json")
HANDOFF_PATH = Path("_incoming/growth-engine.make-bearers.tmp")
OUTPUT_PATH = Path("_incoming/make_production_import.secret.json")
PRODUCTION_BEARER_VARIABLES = {
    "GE_MAKE_BEARER_FB_HANOI": "GE_TEST_BEARER_FB_HANOI",
    "GE_MAKE_BEARER_FB_VENHO": "GE_TEST_BEARER_FB_VENHO",
    "GE_MAKE_BEARER_IG_VENHO": "GE_TEST_BEARER_IG",
}


class ProductionFillError(Exception):
    """Safe-to-display error that never includes a credential value."""


def _production_filter(document: dict[str, Any]) -> None:
    routers = [
        module
        for module in shared._walk_modules(document.get("flow"))
        if module.get("module") == "builtin:BasicRouter"
    ]
    if len(routers) != 1:
        raise ProductionFillError("expected_one_router")
    router_filter = routers[0].get("filter")
    conditions = router_filter.get("conditions") if isinstance(router_filter, dict) else None
    flattened = [
        condition
        for group in conditions or []
        if isinstance(group, list)
        for condition in group
        if isinstance(condition, dict)
    ]
    required = {
        ("{{2.schema_version}}", "growth.command.v2"),
        ("{{2.environment}}", "production"),
    }
    actual = {
        (condition.get("a"), condition.get("b"))
        for condition in flattened
        if condition.get("o") == "text:equal"
    }
    if not required.issubset(actual):
        raise ProductionFillError("production_common_filter_invalid")


def _load_blueprint(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ProductionFillError("blueprint_not_regular_file")
    if stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise ProductionFillError("blueprint_must_be_mode_600")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ProductionFillError("blueprint_unreadable_or_invalid") from error
    if not isinstance(document, dict):
        raise ProductionFillError("blueprint_root_invalid")
    _production_filter(document)
    return document


def fill_production_document(
    document: dict[str, Any],
    handoff: dict[str, str],
    access_client_id: str,
    access_client_secret: str,
) -> tuple[dict[str, Any], dict[str, int]]:
    if set(handoff) != set(PRODUCTION_BEARER_VARIABLES):
        raise ProductionFillError("production_bearer_set_invalid")
    _production_filter(document)
    test_named_bearers = {
        test_name: handoff[production_name]
        for production_name, test_name in PRODUCTION_BEARER_VARIABLES.items()
    }
    try:
        return shared.fill_document(
            document,
            test_named_bearers,
            access_client_id,
            access_client_secret,
            base_url=PRODUCTION_BASE_URL,
        )
    except shared.FillError as error:
        raise ProductionFillError(str(error)) from error


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blueprint", type=Path, default=BLUEPRINT_PATH)
    parser.add_argument("--bearers", type=Path, default=HANDOFF_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        blueprint = _load_blueprint(args.blueprint)
        bearer_values = shared.load_bearer_handoff(
            args.bearers,
            expected_variables=PRODUCTION_BEARER_VARIABLES,
        )
        access_client_id = getpass.getpass("Production Cloudflare Access Client ID (hidden): ")
        access_client_secret = getpass.getpass("Production Cloudflare Access Client Secret (hidden): ")
        filled, counts = fill_production_document(
            blueprint,
            bearer_values,
            access_client_id,
            access_client_secret,
        )
        shared.write_private_json(args.output, filled)
    except (ProductionFillError, shared.FillError) as error:
        print(f"fill_make_production_secrets: {error}", file=sys.stderr)
        return 2
    except Exception:
        print("fill_make_production_secrets: failed safely; check input files and permissions", file=sys.stderr)
        return 2

    print(f"Wrote mode-600 production blueprint: {args.output}")
    print(
        "Replacements: "
        f"base_url={counts['base_url']}, "
        f"bearer_fb_hanoi={counts['bearer_fb_hanoi']}, "
        f"bearer_fb_venho={counts['bearer_fb_venho']}, "
        f"bearer_ig_venho={counts['bearer_ig_venho']}, "
        f"access_client_id={counts['access_client_id']}, "
        f"access_client_secret={counts['access_client_secret']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
