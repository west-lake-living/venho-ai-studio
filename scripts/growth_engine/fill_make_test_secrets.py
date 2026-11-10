#!/usr/bin/env python3
"""Fill TEST-only Make placeholders without printing credential values."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable


BASE_PLACEHOLDER = "https://set-in-make.invalid"
TEST_BASE_URL = "https://ge-test.venhohotel.com"
OUTPUT_PATH = Path("_incoming/make_test_import.secret.json")
PLACEHOLDER_RE = re.compile(r"__SET_IN_MAKE_[A-Z0-9_]+__")
BEARER_RE = re.compile(r"^[A-Za-z0-9_-]{32,}$")
BEARER_VARIABLES = {
    "GE_TEST_BEARER_FB_HANOI": "fb_hanoi",
    "GE_TEST_BEARER_FB_VENHO": "fb_venho",
    "GE_TEST_BEARER_IG": "ig_venho",
}
CHANNEL_BEARER_VARIABLES = {channel: variable for variable, channel in BEARER_VARIABLES.items()}
BEARER_MARKERS = {
    "fb_hanoi": "__SET_IN_MAKE_BEARER_FB_HANOI__",
    "fb_venho": "__SET_IN_MAKE_BEARER_FB_VENHO__",
    "ig_venho": "__SET_IN_MAKE_BEARER_IG_VENHO__",
}
ACCESS_ID_MARKER = "__SET_IN_MAKE_ACCESS_CLIENT_ID__"
ACCESS_SECRET_MARKER = "__SET_IN_MAKE_ACCESS_CLIENT_SECRET__"
ROUTE_CHANNELS = frozenset(BEARER_MARKERS)


class FillError(Exception):
    """Safe-to-display validation error without credential content."""


def _walk_modules(flow: Any) -> Iterable[dict[str, Any]]:
    if not isinstance(flow, list):
        raise FillError("blueprint_flow_invalid")
    for node in flow:
        if not isinstance(node, dict):
            raise FillError("blueprint_module_invalid")
        yield node
        routes = node.get("routes", [])
        if not isinstance(routes, list):
            raise FillError("blueprint_routes_invalid")
        for route in routes:
            if not isinstance(route, dict):
                raise FillError("blueprint_route_invalid")
            if "flow" in route:
                yield from _walk_modules(route["flow"])
        handlers = node.get("onerror", [])
        if not isinstance(handlers, list):
            raise FillError("blueprint_error_handlers_invalid")
        for handler in handlers:
            if isinstance(handler, dict) and isinstance(handler.get("flow"), list):
                yield from _walk_modules(handler["flow"])
            elif isinstance(handler, dict) and isinstance(handler.get("module"), str):
                yield from _walk_modules([handler])


def _channel_from_route(route: dict[str, Any]) -> str:
    flow = route.get("flow")
    if not isinstance(flow, list) or not flow or not isinstance(flow[0], dict):
        raise FillError("router_route_missing_filter")
    filter_data = flow[0].get("filter")
    if not isinstance(filter_data, dict):
        raise FillError("router_route_missing_filter")
    channel = filter_data.get("name")
    if channel not in ROUTE_CHANNELS:
        raise FillError("router_route_channel_invalid")
    conditions = filter_data.get("conditions")
    if not isinstance(conditions, list):
        raise FillError("router_route_condition_invalid")
    matching = [
        condition
        for group in conditions
        if isinstance(group, list)
        for condition in group
        if isinstance(condition, dict)
        and condition.get("a") == "{{2.channel_key}}"
        and condition.get("b") == channel
    ]
    if len(matching) != 1:
        raise FillError("router_route_filter_mismatch")
    return channel


def _router_routes(document: dict[str, Any]) -> dict[str, str]:
    routers = [
        node
        for node in _walk_modules(document.get("flow"))
        if node.get("module") == "builtin:BasicRouter"
    ]
    if len(routers) != 1:
        raise FillError("expected_one_router")
    routes = routers[0].get("routes")
    if not isinstance(routes, list) or len(routes) != 3:
        raise FillError("expected_three_routes")
    result: dict[str, str] = {}
    for index, route in enumerate(routes):
        channel = _channel_from_route(route)
        if channel in result:
            raise FillError("duplicate_router_channel")
        result[channel] = f"route_{index}"
    if set(result) != ROUTE_CHANNELS:
        raise FillError("router_channels_incomplete")
    return result


def _internal_modules_by_route(document: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    routers = [
        node
        for node in _walk_modules(document.get("flow"))
        if node.get("module") == "builtin:BasicRouter"
    ]
    if len(routers) != 1:
        raise FillError("expected_one_router")
    result: dict[str, list[dict[str, Any]]] = {}
    for route in routers[0].get("routes", []):
        channel = _channel_from_route(route)
        modules = list(_walk_modules(route.get("flow")))
        internals = []
        for module in modules:
            if module.get("module") != "http:MakeRequest":
                continue
            mapper = module.get("mapper")
            url = mapper.get("url") if isinstance(mapper, dict) else None
            if isinstance(url, str) and "/internal/" in url:
                internals.append(module)
        if len(internals) != 3:
            raise FillError("expected_three_internal_modules_per_route")
        result[channel] = internals
    all_internal = [
        module
        for module in _walk_modules(document.get("flow"))
        if module.get("module") == "http:MakeRequest"
        and isinstance(module.get("mapper"), dict)
        and isinstance(module["mapper"].get("url"), str)
        and "/internal/" in module["mapper"]["url"]
    ]
    routed_internal = [module for modules in result.values() for module in modules]
    if len(all_internal) != 9 or {id(module) for module in all_internal} != {
        id(module) for module in routed_internal
    }:
        raise FillError("internal_module_route_coverage_invalid")
    return result


def _replace_internal_headers(
    modules_by_route: dict[str, list[dict[str, Any]]],
    bearers: dict[str, str],
    access_client_id: str,
    access_client_secret: str,
) -> dict[str, int]:
    counts = {
        "bearer_fb_hanoi": 0,
        "bearer_fb_venho": 0,
        "bearer_ig_venho": 0,
        "access_client_id": 0,
        "access_client_secret": 0,
    }
    for channel, modules in modules_by_route.items():
        bearer_marker = BEARER_MARKERS[channel]
        bearer_value = bearers[CHANNEL_BEARER_VARIABLES[channel]]
        for module in modules:
            mapper = module.get("mapper")
            if not isinstance(mapper, dict):
                raise FillError("internal_module_mapper_invalid")
            url = mapper.get("url")
            if not isinstance(url, str) or BASE_PLACEHOLDER not in url:
                raise FillError("internal_module_base_placeholder_missing")
            headers = mapper.get("headers")
            if not isinstance(headers, list):
                raise FillError("internal_module_headers_invalid")
            by_name: dict[str, list[dict[str, Any]]] = {}
            for header in headers:
                if isinstance(header, dict) and isinstance(header.get("name"), str):
                    by_name.setdefault(header["name"].casefold(), []).append(header)
            for name in ("authorization", "cf-access-client-id", "cf-access-client-secret"):
                if len(by_name.get(name, [])) != 1:
                    raise FillError("internal_module_required_header_missing_or_duplicate")
            authorization = by_name["authorization"][0]
            access_id_header = by_name["cf-access-client-id"][0]
            access_secret_header = by_name["cf-access-client-secret"][0]
            if authorization.get("value") != f"Bearer {bearer_marker}":
                raise FillError("route_bearer_placeholder_mismatch")
            if access_id_header.get("value") != ACCESS_ID_MARKER:
                raise FillError("access_client_id_placeholder_mismatch")
            if access_secret_header.get("value") != ACCESS_SECRET_MARKER:
                raise FillError("access_client_secret_placeholder_mismatch")
            authorization["value"] = f"Bearer {bearer_value}"
            access_id_header["value"] = access_client_id
            access_secret_header["value"] = access_client_secret
            mapper["url"] = url.replace(BASE_PLACEHOLDER, TEST_BASE_URL)
            counts[f"bearer_{channel}"] += 1
            counts["access_client_id"] += 1
            counts["access_client_secret"] += 1
    return counts


def validate_template(document: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    _router_routes(document)
    modules_by_route = _internal_modules_by_route(document)
    for channel, modules in modules_by_route.items():
        bearer_marker = BEARER_MARKERS[channel]
        for module in modules:
            mapper = module.get("mapper")
            url = mapper.get("url") if isinstance(mapper, dict) else None
            headers = mapper.get("headers") if isinstance(mapper, dict) else None
            if not isinstance(url, str) or BASE_PLACEHOLDER not in url:
                raise FillError("internal_module_base_placeholder_missing")
            if not isinstance(headers, list):
                raise FillError("internal_module_headers_invalid")
            by_name: dict[str, list[dict[str, Any]]] = {}
            for header in headers:
                if isinstance(header, dict) and isinstance(header.get("name"), str):
                    by_name.setdefault(header["name"].casefold(), []).append(header)
            for name in ("authorization", "cf-access-client-id", "cf-access-client-secret"):
                if len(by_name.get(name, [])) != 1:
                    raise FillError("internal_module_required_header_missing_or_duplicate")
            if by_name["authorization"][0].get("value") != f"Bearer {bearer_marker}":
                raise FillError("route_bearer_placeholder_mismatch")
            if by_name["cf-access-client-id"][0].get("value") != ACCESS_ID_MARKER:
                raise FillError("access_client_id_placeholder_mismatch")
            if by_name["cf-access-client-secret"][0].get("value") != ACCESS_SECRET_MARKER:
                raise FillError("access_client_secret_placeholder_mismatch")
    return modules_by_route


def _validate_no_placeholders(document: dict[str, Any]) -> None:
    for value in _all_strings(document):
        if PLACEHOLDER_RE.search(value) or "set-in-make.invalid" in value.casefold():
            raise FillError("unresolved_make_placeholder")


def _all_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _all_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _all_strings(child)


def fill_document(
    document: dict[str, Any],
    bearers: dict[str, str],
    access_client_id: str,
    access_client_secret: str,
) -> tuple[dict[str, Any], dict[str, int]]:
    if set(bearers) != set(BEARER_VARIABLES):
        raise FillError("bearer_set_invalid")
    for bearer in bearers.values():
        if not BEARER_RE.fullmatch(bearer):
            raise FillError("bearer_format_invalid")
    if not _valid_header_value(access_client_id) or not _valid_header_value(access_client_secret):
        raise FillError("access_credential_invalid")

    result = json.loads(json.dumps(document))
    modules_by_route = validate_template(result)
    counts = _replace_internal_headers(modules_by_route, bearers, access_client_id, access_client_secret)
    counts["base_url"] = sum(
        1
        for modules in modules_by_route.values()
        for module in modules
        if TEST_BASE_URL in str(module["mapper"].get("url", ""))
    )
    if counts["base_url"] != 9:
        raise FillError("internal_base_url_replacement_count_invalid")
    _validate_no_placeholders(result)
    return result, counts


def _valid_header_value(value: str) -> bool:
    return (
        bool(value)
        and value == value.strip()
        and not any(ord(character) < 32 or ord(character) == 127 for character in value)
        and not PLACEHOLDER_RE.search(value)
    )


def load_bearer_handoff(path: Path) -> dict[str, str]:
    if path.is_symlink() or not path.is_file():
        raise FillError("bearer_handoff_not_regular_file")
    if stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise FillError("bearer_handoff_must_be_mode_600")
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise FillError("bearer_handoff_unreadable") from error
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            raise FillError("bearer_handoff_format_invalid")
        name, value = stripped.split("=", 1)
        if name not in BEARER_VARIABLES or name in values or not BEARER_RE.fullmatch(value):
            raise FillError("bearer_handoff_format_invalid")
        values[name] = value
    if set(values) != set(BEARER_VARIABLES):
        raise FillError("bearer_handoff_incomplete")
    return values


def write_private_json(path: Path, document: dict[str, Any]) -> None:
    if path.is_symlink() or path.parent.is_symlink() or not path.parent.is_dir():
        raise FillError("output_path_invalid")
    encoded = (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".make_test_import.secret.json.", suffix=".secret.json", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    except OSError as error:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise FillError("output_write_failed") from error


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blueprint", type=Path, default=Path("_incoming/make_test_import.json"))
    parser.add_argument("--bearers", type=Path, default=Path("_incoming/growth-engine-test.make-bearers.tmp"))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if args.blueprint.is_symlink() or not args.blueprint.is_file():
            raise FillError("blueprint_not_regular_file")
        try:
            source = json.loads(args.blueprint.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise FillError("blueprint_unreadable_or_invalid") from error
        if not isinstance(source, dict):
            raise FillError("blueprint_root_invalid")
        bearers = load_bearer_handoff(args.bearers)
        validate_template(source)
        access_client_id = getpass.getpass("Cloudflare Access Client ID (hidden): ")
        access_client_secret = getpass.getpass("Cloudflare Access Client Secret (hidden): ")
        filled, counts = fill_document(source, bearers, access_client_id, access_client_secret)
        write_private_json(OUTPUT_PATH, filled)
    except FillError as error:
        print(f"fill_make_test_secrets: {error}", file=sys.stderr)
        return 2
    except Exception:
        print("fill_make_test_secrets: failed safely; check input files and permissions", file=sys.stderr)
        return 2

    print(f"Wrote mode-600 TEST blueprint: {OUTPUT_PATH}")
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
