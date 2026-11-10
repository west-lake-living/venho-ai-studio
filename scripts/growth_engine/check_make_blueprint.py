#!/usr/bin/env python3
"""Validate a Make blueprint without printing any blueprint values."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit


MAPPING_RE = re.compile(r"\{\{\s*(\d+)\.([A-Za-z_][A-Za-z0-9_.-]*)")
URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
SIGNED_QUERY_RE = re.compile(
    r"(?:access_token|api_key|authorization|signature|sig|token|x-amz-signature)\s*=\s*([^&#\s]+)",
    re.IGNORECASE,
)
TOKEN_PATTERNS = (
    re.compile(r"\bEA[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bBearer\s+(?!__SET_IN_MAKE_)[A-Za-z0-9._~+-]{16,}", re.IGNORECASE),
    re.compile(
        r"\b(?=[A-Za-z0-9._~-]{40,}\b)(?=[A-Za-z0-9._~-]*[A-Za-z])"
        r"(?=[A-Za-z0-9._~-]*\d)[A-Za-z0-9._~-]+\b"
    ),
)


@dataclass(frozen=True)
class CheckResult:
    errors: tuple[str, ...]
    module_count: int
    route_count: int
    mapping_count: int


def _strings(value: Any, *, skip_keys: frozenset[str] = frozenset()) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, child in value.items():
            if key not in skip_keys:
                yield from _strings(child, skip_keys=skip_keys)
    elif isinstance(value, list):
        for child in value:
            yield from _strings(child, skip_keys=skip_keys)


def _modules(flow: Any) -> Iterable[dict[str, Any]]:
    if not isinstance(flow, list):
        return
    for node in flow:
        if not isinstance(node, dict):
            continue
        yield node
        routes = node.get("routes", [])
        if isinstance(routes, list):
            for route in routes:
                if isinstance(route, dict):
                    yield from _modules(route.get("flow"))
        handlers = node.get("onerror", [])
        if isinstance(handlers, list):
            for handler in handlers:
                if isinstance(handler, dict):
                    if isinstance(handler.get("flow"), list):
                        yield from _modules(handler["flow"])
                    elif isinstance(handler.get("module"), str):
                        yield handler


def _secret_scan(value: Any) -> set[str]:
    categories: set[str] = set()
    for text in _strings(value):
        for url in URL_RE.findall(text):
            host = (urlsplit(url).hostname or "").lower()
            placeholder_host = (
                host == "set-in-make.invalid"
                or (host.startswith("__set_in_make_") and host.endswith("__"))
            )
            if not placeholder_host:
                categories.add("literal_url")
        for match in SIGNED_QUERY_RE.finditer(text):
            query_value = match.group(1)
            if "__SET_IN_MAKE_" not in query_value and "{{" not in query_value:
                categories.add("signed_url_value")
        for pattern in TOKEN_PATTERNS:
            if pattern.search(text):
                categories.add("token_like_literal")
    return categories


def _validate_flow(
    flow: Any,
    visible_ids: set[int],
    global_ids: set[int],
    errors: set[str],
    counters: dict[str, int],
) -> None:
    if not isinstance(flow, list):
        errors.add("invalid_flow")
        return

    visible = set(visible_ids)
    for node in flow:
        if not isinstance(node, dict):
            errors.add("invalid_module")
            continue

        module_id = node.get("id")
        if not isinstance(module_id, int) or isinstance(module_id, bool) or module_id <= 0:
            errors.add("invalid_module_id")
            module_id = None
        elif module_id in global_ids:
            errors.add("duplicate_module_id")
        else:
            global_ids.add(module_id)
            counters["modules"] += 1

        if not isinstance(node.get("module"), str):
            errors.add("invalid_module_type")

        payload = {key: value for key, value in node.items() if key not in {"routes", "onerror"}}
        for text in _strings(payload):
            for reference in MAPPING_RE.finditer(text):
                counters["mappings"] += 1
                source_id = int(reference.group(1))
                if source_id not in global_ids:
                    errors.add("mapping_source_missing_or_forward")
                elif source_id not in visible:
                    errors.add("mapping_source_not_preceding")

        next_visible = set(visible)
        if module_id is not None:
            next_visible.add(module_id)

        routes = node.get("routes", [])
        if routes:
            if not isinstance(routes, list):
                errors.add("invalid_routes")
            else:
                for route in routes:
                    counters["routes"] += 1
                    if not isinstance(route, dict) or not isinstance(route.get("flow"), list):
                        errors.add("invalid_route")
                        continue
                    route_payload = {key: value for key, value in route.items() if key != "flow"}
                    for text in _strings(route_payload):
                        for reference in MAPPING_RE.finditer(text):
                            counters["mappings"] += 1
                            source_id = int(reference.group(1))
                            if source_id not in global_ids:
                                errors.add("mapping_source_missing_or_forward")
                            elif source_id not in next_visible:
                                errors.add("mapping_source_not_preceding")
                    _validate_flow(route["flow"], next_visible, global_ids, errors, counters)

        handlers = node.get("onerror", [])
        if handlers:
            if not isinstance(handlers, list):
                errors.add("invalid_error_handlers")
            else:
                for handler in handlers:
                    if isinstance(handler, dict) and isinstance(handler.get("flow"), list):
                        _validate_flow(handler["flow"], next_visible, global_ids, errors, counters)
                    elif isinstance(handler, dict) and isinstance(handler.get("module"), str):
                        _validate_flow([handler], next_visible, global_ids, errors, counters)
                    else:
                        errors.add("invalid_error_handler_shape")

        if module_id is not None:
            visible.add(module_id)


def validate_blueprint(document: Any) -> CheckResult:
    errors: set[str] = set()
    counters = {"modules": 0, "routes": 0, "mappings": 0}
    if not isinstance(document, dict) or not isinstance(document.get("flow"), list):
        return CheckResult(("invalid_blueprint_root",), 0, 0, 0)

    errors.update(_secret_scan(document))

    _validate_flow(document["flow"], set(), set(), errors, counters)
    modules_by_id = {
        module["id"]: module
        for module in _modules(document["flow"])
        if isinstance(module.get("id"), int)
    }
    for module in modules_by_id.values():
        for text in _strings(module):
            for reference in MAPPING_RE.finditer(text):
                source = modules_by_id.get(int(reference.group(1)))
                if (
                    source is not None
                    and source.get("module") == "facebook-pages:CreatePostWithPhotos"
                    and reference.group(2) == "post_id"
                ):
                    errors.add("facebook_receipt_must_use_module_id")
    return CheckResult(
        tuple(sorted(errors)),
        counters["modules"],
        counters["routes"],
        counters["mappings"],
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "blueprint",
        nargs="?",
        type=Path,
        default=Path("_incoming/make_test_import.json"),
    )
    args = parser.parse_args(argv)

    try:
        document = json.loads(args.blueprint.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        print("FAIL: blueprint unavailable or invalid JSON")
        return 2

    result = validate_blueprint(document)
    if result.errors:
        print(
            "FAIL: static check ("
            + ", ".join(result.errors)
            + f"); modules={result.module_count}, routes={result.route_count}, "
            + f"mappings={result.mapping_count}"
        )
        return 1
    print(
        "PASS: static check; "
        f"modules={result.module_count}, routes={result.route_count}, "
        f"mappings={result.mapping_count}, secret_scan=clear"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
