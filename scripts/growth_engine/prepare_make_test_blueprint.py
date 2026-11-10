#!/usr/bin/env python3
"""Prepare an ignored Make TEST import draft from the operator's export."""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from scripts.growth_engine.check_make_blueprint import validate_blueprint
except ModuleNotFoundError as error:
    if error.name != "scripts":
        raise
    from check_make_blueprint import validate_blueprint


SOURCE = Path("_incoming/make_test_export.json")
TARGET = Path("_incoming/make_test_import.json")
PLACEHOLDER_BASE = "https://set-in-make.invalid"
ACCESS_ID = "__SET_IN_MAKE_ACCESS_CLIENT_ID__"
ACCESS_SECRET = "__SET_IN_MAKE_ACCESS_CLIENT_SECRET__"


class PreparationError(ValueError):
    """A safe, non-value-bearing preparation error."""


@dataclass(frozen=True)
class RawJson:
    expression: str


def _walk(flow: Any):
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
                    yield from _walk(route.get("flow"))
        handlers = node.get("onerror", [])
        if isinstance(handlers, list):
            for handler in handlers:
                if isinstance(handler, dict):
                    if isinstance(handler.get("flow"), list):
                        yield from _walk(handler["flow"])
                    elif isinstance(handler.get("module"), str):
                        yield handler


def _index_modules(document: dict[str, Any]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for module in _walk(document.get("flow")):
        module_id = module.get("id")
        if isinstance(module_id, int):
            if module_id in result:
                raise PreparationError("duplicate_source_module_id")
            result[module_id] = module
    return result


def _render_json(value: Any) -> str:
    if isinstance(value, RawJson):
        return value.expression
    if isinstance(value, dict):
        items = [f"{json.dumps(str(key), ensure_ascii=False)}:{_render_json(child)}" for key, child in value.items()]
        return "{" + ",".join(items) + "}"
    if isinstance(value, list):
        return "[" + ",".join(_render_json(child) for child in value) + "]"
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _field(expression: str) -> str:
    return "{{" + expression + "}}"


def _replace_module_reference(value: Any, old_id: int, new_id: int) -> Any:
    if isinstance(value, str):
        return re.sub(rf"(?<=\{{\{{){old_id}(?=\.)", str(new_id), value)
    if isinstance(value, list):
        return [_replace_module_reference(child, old_id, new_id) for child in value]
    if isinstance(value, dict):
        return {key: _replace_module_reference(child, old_id, new_id) for key, child in value.items()}
    return value


def _make_filter(name: str, conditions: list[dict[str, Any]]) -> dict[str, Any]:
    return {"name": name, "conditions": [conditions]}


def _condition(left: str, operator: str, right: str) -> dict[str, str]:
    return {"a": left, "o": operator, "b": right}


def _position(module: dict[str, Any], x: int, y: int) -> None:
    metadata = module.get("metadata")
    if isinstance(metadata, dict):
        designer = metadata.get("designer")
        if isinstance(designer, dict):
            designer["x"] = x
            designer["y"] = y


def _set_restore_header_count(module: dict[str, Any], count: int) -> None:
    metadata = module.get("metadata")
    if not isinstance(metadata, dict):
        return
    restore = metadata.get("restore")
    if not isinstance(restore, dict):
        return
    expect = restore.get("expect")
    if not isinstance(expect, dict):
        return
    headers = expect.get("headers")
    if isinstance(headers, dict) and isinstance(headers.get("items"), list):
        headers["items"] = [None] * count


def _headers(principal: str) -> list[dict[str, str]]:
    return [
        {"name": "Authorization", "value": f"Bearer __SET_IN_MAKE_BEARER_{principal}__"},
        {"name": "CF-Access-Client-Id", "value": ACCESS_ID},
        {"name": "CF-Access-Client-Secret", "value": ACCESS_SECRET},
    ]


def _request(
    template: dict[str, Any],
    *,
    module_id: int,
    method: str,
    url: str,
    principal: str | None,
    body: dict[str, Any] | None,
    parse_response: bool,
    x: int,
    y: int,
    filter_value: dict[str, Any] | None = None,
) -> dict[str, Any]:
    request = copy.deepcopy(template)
    request["id"] = module_id
    request.pop("onerror", None)
    request["mapper"]["url"] = url
    # Make's exported HTTP blueprint serializes the method enum in lowercase.
    request["mapper"]["method"] = method.lower()
    request["mapper"]["headers"] = _headers(principal) if principal else []
    if body is None:
        for key in ("contentType", "inputMethod", "jsonStringBodyContent"):
            request["mapper"].pop(key, None)
    else:
        request["mapper"]["jsonStringBodyContent"] = _render_json(body)
    request["mapper"]["parseResponse"] = parse_response
    request["mapper"]["timeout"] = "30"
    if filter_value is None:
        request.pop("filter", None)
    else:
        request["filter"] = copy.deepcopy(filter_value)
    _set_restore_header_count(request, len(request["mapper"]["headers"]))
    _position(request, x, y)
    return request


def _receipt_body(
    authorize_id: int,
    outcome: str,
    *,
    platform_post_id: str | None,
) -> dict[str, Any]:
    grant = f"{authorize_id}.data.grant_id"
    is_success = outcome == "POST_CREATED"
    return {
        "schema_version": "growth.receipt.v2",
        "event_id": f"{_field(grant)}:{outcome}",
        "command_id": _field("2.command_id"),
        "execution_id": _field(f"{authorize_id}.data.execution_id"),
        "grant_id": _field(grant),
        "delivery_id": _field("2.delivery_id"),
        "revision_id": _field("2.revision_id"),
        "channel_id": _field("2.channel_id"),
        "remote_page_id": _field("2.remote_page_id"),
        "payload_hash": _field("2.payload_hash"),
        "outcome": outcome,
        "platform_post_id": _field(platform_post_id) if platform_post_id else None,
        "permalink": None,
        "failed_step": None if is_success else "CREATE_POST",
        "error": None,
        "occurred_at_ms": RawJson('{{formatDate(now; "x")}}'),
    }


def _authorize_body(media_id: int) -> dict[str, Any]:
    return {
        "schema_version": "growth.authorize.v2",
        "command_token": _field("2.command_token"),
        "payload_hash": _field("2.payload_hash"),
        "media_report": {
            "http_status": RawJson(_field(f"{media_id}.statusCode")),
            "content_type": _field(f"{media_id}.headers.content-type"),
        },
    }


def _media_filter(media_id: int, name: str) -> dict[str, Any]:
    return _make_filter(
        name,
        [
            _condition(_field(f"{media_id}.statusCode"), "number:equal", "200"),
            _condition(_field(f"{media_id}.headers.content-type"), "text:equal", "image/jpeg"),
        ],
    )


def _grant_filter(authorize_id: int, name: str) -> dict[str, Any]:
    now_ms = '{{formatDate(now; "x")}}'
    return _make_filter(
        name,
        [
            _condition(_field(f"{authorize_id}.data.execute"), "boolean:equal", "true"),
            _condition(now_ms, "number:less", _field(f"{authorize_id}.data.grant_expires_at_ms")),
        ],
    )


def _receipt_request(
    template: dict[str, Any],
    *,
    module_id: int,
    authorize_id: int,
    outcome: str,
    principal: str,
    y: int,
    platform_id_ref: str | None,
) -> dict[str, Any]:
    return _request(
        template,
        module_id=module_id,
        method="POST",
        url=f"{PLACEHOLDER_BASE}/internal/growth/v2/receipts",
        principal=principal,
        body=_receipt_body(authorize_id, outcome, platform_post_id=platform_id_ref),
        parse_response=True,
        x=1160,
        y=y,
    )


def prepare_blueprint(document: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(document)
    source_metadata = document.get("metadata")
    if not isinstance(source_metadata, dict) or source_metadata.get("instant") is not True:
        raise PreparationError("source_not_immediate")
    metadata = result.get("metadata")
    if not isinstance(metadata, dict):
        raise PreparationError("missing_scenario_metadata")
    metadata["instant"] = source_metadata["instant"]
    scenario_metadata = metadata.get("scenario")
    if not isinstance(scenario_metadata, dict):
        raise PreparationError("missing_scenario_settings")
    scenario_metadata["sequential"] = True

    flow = result.get("flow")
    if not isinstance(flow, list) or len(flow) != 3:
        raise PreparationError("unexpected_root_flow")
    if [node.get("id") for node in flow] != [2, 4, 5]:
        raise PreparationError("unexpected_root_module_order")
    webhook, download, router = flow
    if webhook.get("module") != "gateway:CustomWebHook" or download.get("module") != "http:DownloadFile":
        raise PreparationError("unexpected_webhook_or_download_module")
    if router.get("module") != "builtin:BasicRouter" or len(router.get("routes", [])) != 3:
        raise PreparationError("unexpected_router_shape")

    routes = router["routes"]
    expected = [(3, 8), (6, 7), (12, 13)]
    posts: list[dict[str, Any]] = []
    route_filters: list[dict[str, Any]] = []
    for route, (post_id, response_id) in zip(routes, expected):
        route_flow = route.get("flow")
        if not isinstance(route_flow, list) or len(route_flow) != 2:
            raise PreparationError("unexpected_route_flow")
        post, response = route_flow
        if post.get("id") != post_id or response.get("id") != response_id:
            raise PreparationError("unexpected_route_module_order")
        if response.get("module") != "gateway:WebhookRespond":
            raise PreparationError("unexpected_response_module")
        route_filter = post.get("filter")
        if not isinstance(route_filter, dict):
            raise PreparationError("missing_channel_filter")
        posts.append(post)
        route_filters.append(copy.deepcopy(route_filter))

    if posts[0].get("module") != "facebook-pages:CreatePostWithPhotos":
        raise PreparationError("unexpected_facebook_module")
    if posts[1].get("module") != "instagram-business:CreatePostPhoto":
        raise PreparationError("unexpected_instagram_module")
    if posts[2].get("module") != "facebook-pages:CreatePostWithPhotos":
        raise PreparationError("unexpected_facebook_module")

    template_request = next(
        (module for module in posts[0].get("onerror", []) if isinstance(module, dict) and module.get("id") == 14),
        None,
    )
    template_ignore = next(
        (module for module in posts[0].get("onerror", []) if isinstance(module, dict) and module.get("id") == 15),
        None,
    )
    if not isinstance(template_request, dict) or template_request.get("module") != "http:MakeRequest":
        raise PreparationError("missing_http_request_template")
    if not isinstance(template_ignore, dict) or template_ignore.get("module") != "builtin:Ignore":
        raise PreparationError("missing_ignore_directive_template")
    mapper = template_request.get("mapper")
    if not isinstance(mapper, dict) or str(mapper.get("method", "")).upper() != "POST":
        raise PreparationError("invalid_http_request_template")
    header_names = {
        header.get("name")
        for header in mapper.get("headers", [])
        if isinstance(header, dict)
    }
    if not {"Authorization", "CF-Access-Client-Id"}.issubset(header_names):
        raise PreparationError("unexpected_http_header_template")
    if not isinstance(mapper.get("jsonStringBodyContent"), str):
        raise PreparationError("missing_json_body_template")

    common_filter = download.get("filter")
    if not isinstance(common_filter, dict):
        raise PreparationError("missing_common_filter")
    router["filter"] = copy.deepcopy(common_filter)
    del download["filter"]

    request_template = copy.deepcopy(template_request)
    ignore_template = copy.deepcopy(template_ignore)
    posts[0].pop("onerror", None)

    fb1_y = int(posts[0].get("metadata", {}).get("designer", {}).get("y", -299))
    ig_y = int(posts[1].get("metadata", {}).get("designer", {}).get("y", 1))
    fb2_y = int(posts[2].get("metadata", {}).get("designer", {}).get("y", 301))

    # Preserve the existing Facebook image download as fb_hanoi F1 and clone it for fb_venho.
    fb1_image = download
    fb1_image["filter"] = route_filters[0]
    fb1_image["mapper"]["url"] = _field("2.media_url")
    _position(fb1_image, 560, fb1_y)
    fb2_image = copy.deepcopy(download)
    fb2_image["id"] = 20
    fb2_image["filter"] = route_filters[2]
    fb2_image["mapper"]["url"] = _field("2.media_url")
    _position(fb2_image, 560, fb2_y)

    # The original router route filters move to each branch's first module.
    auth1 = _request(
        request_template,
        module_id=16,
        method="POST",
        url=f"{PLACEHOLDER_BASE}/internal/growth/v2/executions/authorize",
        principal="FB_HANOI",
        body=_authorize_body(4),
        parse_response=True,
        x=760,
        y=fb1_y,
        filter_value=_media_filter(4, "F1 image valid"),
    )
    auth2 = _request(
        request_template,
        module_id=21,
        method="POST",
        url=f"{PLACEHOLDER_BASE}/internal/growth/v2/executions/authorize",
        principal="FB_VENHO",
        body=_authorize_body(20),
        parse_response=True,
        x=760,
        y=fb2_y,
        filter_value=_media_filter(20, "F1 image valid"),
    )
    auth_ig = _request(
        request_template,
        module_id=26,
        method="POST",
        url=f"{PLACEHOLDER_BASE}/internal/growth/v2/executions/authorize",
        principal="IG_VENHO",
        body=_authorize_body(25),
        parse_response=True,
        x=760,
        y=ig_y,
        filter_value=_media_filter(25, "I1 media URL valid"),
    )

    grant1 = _grant_filter(16, "F3 authorize grant valid")
    grant2 = _grant_filter(21, "F3 authorize grant valid")
    grant_ig = _grant_filter(26, "I3 authorize grant valid")
    posts[0]["filter"] = grant1
    posts[2]["filter"] = grant2
    posts[1]["filter"] = grant_ig

    # Use the authorized caption and the branch-local binary for Facebook; Instagram keeps the URL.
    posts[0]["mapper"]["message"] = _field("16.data.caption")
    posts[0]["mapper"]["photos"][0]["data"] = _field("4.data")
    posts[2]["mapper"]["message"] = _field("21.data.caption")
    posts[2]["mapper"]["photos"] = _replace_module_reference(posts[2]["mapper"]["photos"], 4, 20)
    posts[2]["mapper"]["photos"][0]["data"] = _field("20.data")
    posts[1]["mapper"]["caption"] = _field("26.data.caption")
    posts[1]["mapper"]["image_url"] = _field("2.media_url")

    # Success receipts follow posting; error receipts are conservative and never retry/resume the post.
    f5_hanoi = _receipt_request(
        request_template, module_id=17, authorize_id=16, outcome="POST_CREATED",
        principal="FB_HANOI", y=fb1_y, platform_id_ref="3.id",
    )
    f5_venho = _receipt_request(
        request_template, module_id=22, authorize_id=21, outcome="POST_CREATED",
        principal="FB_VENHO", y=fb2_y, platform_id_ref="12.id",
    )
    i5_venho = _receipt_request(
        request_template, module_id=27, authorize_id=26, outcome="POST_CREATED",
        principal="IG_VENHO", y=ig_y, platform_id_ref="6.id",
    )
    f6_hanoi = _receipt_request(
        request_template, module_id=18, authorize_id=16, outcome="OUTCOME_UNKNOWN",
        principal="FB_HANOI", y=fb1_y + 130, platform_id_ref=None,
    )
    f6_venho = _receipt_request(
        request_template, module_id=23, authorize_id=21, outcome="OUTCOME_UNKNOWN",
        principal="FB_VENHO", y=fb2_y + 130, platform_id_ref=None,
    )
    i6_venho = _receipt_request(
        request_template, module_id=28, authorize_id=26, outcome="OUTCOME_UNKNOWN",
        principal="IG_VENHO", y=ig_y + 130, platform_id_ref=None,
    )
    ignore1 = copy.deepcopy(ignore_template)
    ignore1["id"] = 19
    ignore2 = copy.deepcopy(ignore_template)
    ignore2["id"] = 24
    ignore_ig = copy.deepcopy(ignore_template)
    ignore_ig["id"] = 29
    _position(f6_hanoi, 1160, fb1_y + 130)
    _position(f6_venho, 1160, fb2_y + 130)
    _position(i6_venho, 1160, ig_y + 130)
    _position(ignore1, 1360, fb1_y + 130)
    _position(ignore2, 1360, fb2_y + 130)
    _position(ignore_ig, 1360, ig_y + 130)
    posts[0]["onerror"] = [f6_hanoi, ignore1]
    posts[2]["onerror"] = [f6_venho, ignore2]
    posts[1]["onerror"] = [i6_venho, ignore_ig]

    # The I1 request validates the URL without mapping its binary into Instagram.
    i1 = _request(
        request_template,
        module_id=25,
        method="GET",
        url=_field("2.media_url"),
        principal=None,
        body=None,
        parse_response=False,
        x=560,
        y=ig_y,
        filter_value=route_filters[1],
    )

    # Sequential processing does not support explicit Webhook response modules.
    routes[0]["flow"] = [fb1_image, auth1, posts[0], f5_hanoi]
    routes[1]["flow"] = [i1, auth_ig, posts[1], i5_venho]
    routes[2]["flow"] = [fb2_image, auth2, posts[2], f5_venho]

    result["flow"] = [webhook, router]
    return result


def _write_private(path: Path, document: dict[str, Any]) -> None:
    payload = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(payload)
    os.chmod(path, 0o600)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=TARGET)
    args = parser.parse_args(argv)

    try:
        source = json.loads(args.source.read_text(encoding="utf-8"))
        prepared = prepare_blueprint(source)
    except (OSError, UnicodeError, json.JSONDecodeError):
        print("FAIL: source unavailable or invalid JSON")
        return 2
    except PreparationError as error:
        print(f"FAIL: unsupported export structure ({error})")
        return 3

    checked = validate_blueprint(prepared)
    if checked.errors:
        print("FAIL: output validation (" + ", ".join(checked.errors) + ")")
        return 4
    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        _write_private(args.output, prepared)
    except FileExistsError:
        print("FAIL: output already exists; refusing to overwrite")
        return 5
    except OSError:
        print("FAIL: could not write private output")
        return 6

    print(
        "PASS: prepared ignored TEST draft; "
        f"modules={checked.module_count}, routes={checked.route_count}, "
        f"mappings={checked.mapping_count}, secret_scan=clear, mode=600"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
