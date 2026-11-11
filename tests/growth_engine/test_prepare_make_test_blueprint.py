from __future__ import annotations

import json
import stat

from scripts.growth_engine.check_make_blueprint import validate_blueprint
from scripts.growth_engine.prepare_make_test_blueprint import main, prepare_blueprint


def _module(
    module_id: int,
    module_type: str,
    *,
    mapper=None,
    parameters=None,
    metadata=None,
    filter_value=None,
    onerror=None,
) -> dict:
    value = {
        "id": module_id,
        "module": module_type,
        "version": 1,
        "parameters": parameters or {},
        "mapper": mapper or {},
        "metadata": metadata or {"designer": {"x": module_id * 10, "y": 0}},
    }
    if filter_value is not None:
        value["filter"] = filter_value
    if onerror is not None:
        value["onerror"] = onerror
    return value


def _filter(name: str, field: str, value: str) -> dict:
    return {
        "name": name,
        "conditions": [[{"a": f"{{{{2.{field}}}}}", "o": "text:equal", "b": value}]],
    }


def source_blueprint() -> dict:
    common = {
        "name": "v2 TEST common",
        "conditions": [[
            {"a": "{{2.schema_version}}", "o": "text:equal", "b": "growth.command.v2"},
            {"a": "{{2.environment}}", "o": "text:equal", "b": "test"},
        ]],
    }
    download = _module(
        4,
        "http:DownloadFile",
        mapper={"url": "{{2.media_url}}", "shareCookies": False, "stopOnHttpError": True},
        parameters={"authenticationType": "none"},
        filter_value=common,
    )
    request = _module(
        14,
        "http:MakeRequest",
        mapper={
            "url": "https://set-in-make.invalid/template",
            "method": "post",
            "headers": [
                {"name": "Authorization", "value": "Bearer __SET_IN_MAKE_BEARER_TEMPLATE__"},
                {"name": "CF-Access-Client-Id", "value": "__SET_IN_MAKE_ACCESS_CLIENT_ID__"},
            ],
            "contentType": "json",
            "parseResponse": True,
            "stopOnHttpError": True,
            "timeout": "30",
            "allowRedirects": False,
            "shareCookies": False,
            "requestCompressedContent": False,
            "inputMethod": "jsonString",
            "jsonStringBodyContent": '{"command_id":"{{2.command_id}}","channel_key":"{{2.channel_key}}"}',
        },
        parameters={"authenticationType": "none", "tlsType": "strict"},
        metadata={
            "designer": {"x": 900, "y": -100},
            "interface": [{"name": "data"}, {"name": "statusCode"}, {"name": "headers"}],
            "restore": {"expect": {"headers": {"items": [None, None]}}},
        },
    )
    ignore = _module(15, "builtin:Ignore")
    fb_hanoi = _module(
        3,
        "facebook-pages:CreatePostWithPhotos",
        mapper={"page_id": "test-page-a", "message": "{{2.content.text}}", "photos": [{"data": "{{4.data}}", "fileName": "test.jpg", "type": "data"}]},
        filter_value=_filter("fb_hanoi", "channel_key", "fb_hanoi"),
        onerror=[request, ignore],
    )
    ig = _module(
        6,
        "instagram-business:CreatePostPhoto",
        mapper={"accountId": "test-ig", "image_url": "{{2.media_url}}", "caption": "{{2.content.text}}"},
        filter_value=_filter("ig_venho", "channel_key", "ig_venho"),
    )
    fb_venho = _module(
        12,
        "facebook-pages:CreatePostWithPhotos",
        mapper={"page_id": "test-page-b", "message": "{{2.content.text}}", "photos": [{"data": "{{4.data}}", "fileName": "test.jpg", "type": "data"}]},
        filter_value=_filter("fb_venho", "channel_key", "fb_venho"),
    )
    responses = [
        _module(8, "gateway:WebhookRespond", mapper={"status": 200, "body": "https://legacy.invalid/fb-hanoi", "headers": []}),
        _module(7, "gateway:WebhookRespond", mapper={"status": 200, "body": "https://legacy.invalid/instagram", "headers": []}),
        _module(13, "gateway:WebhookRespond", mapper={"status": 200, "body": "ack", "headers": []}),
    ]
    return {
        "name": "synthetic TEST scenario",
        "metadata": {"instant": True, "scenario": {"sequential": False}},
        "flow": [
            _module(2, "gateway:CustomWebHook", mapper={}, parameters={"hook": 1, "maxResults": 1}),
            download,
            _module(
                5,
                "builtin:BasicRouter",
                mapper=None,
                parameters={},
                metadata={"designer": {"x": 700, "y": 0}},
                filter_value=None,
            ) | {
                "mapper": None,
                "routes": [
                    {"flow": [fb_hanoi, responses[0]]},
                    {"flow": [ig, responses[1]]},
                    {"flow": [fb_venho, responses[2]]},
                ],
            },
        ],
    }


def test_prepares_three_routes_with_local_media_authorize_and_receipts() -> None:
    source = source_blueprint()
    prepared = prepare_blueprint(source)
    result = validate_blueprint(prepared)

    assert result.errors == ()
    assert result.route_count == 3
    assert result.module_count == 26
    assert prepared["metadata"]["instant"] is True
    assert prepared["metadata"]["scenario"]["sequential"] is True
    assert all(module["module"] != "gateway:WebhookRespond" for module in _all_modules(prepared))
    assert 14 not in {module["id"] for module in _all_modules(prepared)}
    assert 15 not in {module["id"] for module in _all_modules(prepared)}
    routes = prepared["flow"][1]["routes"]
    assert [[module["id"] for module in route["flow"]] for route in routes] == [
        [4, 16, 3, 17],
        [25, 26, 6, 27],
        [20, 21, 12, 22],
    ]
    assert [module["id"] for module in routes[0]["flow"][2]["onerror"]] == [18, 19]
    assert [module["id"] for module in routes[1]["flow"][2]["onerror"]] == [28, 29]
    assert [module["id"] for module in routes[2]["flow"][2]["onerror"]] == [23, 24]
    assert [module["id"] for module in routes[0]["flow"][0]["onerror"]] == [30]
    assert [module["id"] for module in routes[1]["flow"][0]["onerror"]] == [32]
    assert [module["id"] for module in routes[2]["flow"][0]["onerror"]] == [31]
    assert [module["id"] for module in routes[0]["flow"][1]["onerror"]] == [33]
    assert [module["id"] for module in routes[1]["flow"][1]["onerror"]] == [35]
    assert [module["id"] for module in routes[2]["flow"][1]["onerror"]] == [34]
    assert all(
        module["module"] == "builtin:Ignore"
        for route in routes
        for module in route["flow"][0]["onerror"]
    )
    assert routes[0]["flow"][2]["mapper"]["photos"][0]["data"] == "{{4.data}}"
    assert routes[2]["flow"][2]["mapper"]["photos"][0]["data"] == "{{20.data}}"
    assert routes[0]["flow"][2]["mapper"]["message"] == "{{16.data.caption}}"
    assert routes[1]["flow"][2]["mapper"]["image_url"] == "{{2.media_url}}"
    assert routes[0]["flow"][1]["mapper"]["method"] == "post"
    assert routes[0]["flow"][3]["mapper"]["method"] == "post"
    assert routes[1]["flow"][0]["mapper"]["method"] == "get"
    assert not {"contentType", "inputMethod", "jsonStringBodyContent"} & set(routes[1]["flow"][0]["mapper"])
    assert '"platform_post_id":"{{3.id}}"' in routes[0]["flow"][3]["mapper"]["jsonStringBodyContent"]
    assert '"platform_post_id":"{{12.id}}"' in routes[2]["flow"][3]["mapper"]["jsonStringBodyContent"]
    assert "{{3.post_id}}" not in json.dumps(prepared)
    assert "{{12.post_id}}" not in json.dumps(prepared)
    for route in routes:
        assert "headers.`content-type`" in route["flow"][1]["mapper"]["jsonStringBodyContent"]
        assert "headers.`content-type`" in route["flow"][1]["filter"]["conditions"][0][1]["a"]
    assert prepared["flow"][1]["filter"] == source["flow"][1]["filter"]
    assert source["flow"][2]["routes"][0]["flow"][1]["mapper"]["body"].startswith("https://")


def test_production_mode_targets_verified_accounts_and_filters_production_envelopes() -> None:
    prepared = prepare_blueprint(source_blueprint(), environment="production")
    result = validate_blueprint(prepared)
    routes = prepared["flow"][1]["routes"]
    fb_hanoi, ig_venho, fb_venho = routes

    assert result.errors == ()
    assert prepared["flow"][1]["filter"]["conditions"][0][1]["b"] == "production"
    assert fb_hanoi["flow"][2]["mapper"]["page_id"] == "1124616474074140"
    assert fb_venho["flow"][2]["mapper"]["page_id"] == "803531149684177"
    assert ig_venho["flow"][2]["mapper"]["accountId"] == "17841457936965829"
    assert [route["flow"][0]["filter"]["conditions"][0][0]["b"] for route in routes] == [
        "fb_hanoi", "ig_venho", "fb_venho"
    ]
    assert all("https://set-in-make.invalid" in str(route["flow"]) for route in routes)


def test_production_generation_rejects_unknown_destination_field() -> None:
    source = source_blueprint()
    source["flow"][2]["routes"][0]["flow"][0]["mapper"].pop("page_id")
    try:
        prepare_blueprint(source, environment="production")
    except ValueError as error:
        assert "destination_field" in str(error)
    else:
        raise AssertionError("production target must not be guessed")


def test_authorize_http_errors_end_in_ignore_without_post_or_receipt() -> None:
    prepared = prepare_blueprint(source_blueprint())
    routes = prepared["flow"][1]["routes"]

    for route in routes:
        authorize = route["flow"][1]
        assert authorize["module"] == "http:MakeRequest"
        assert [item["module"] for item in authorize["onerror"]] == ["builtin:Ignore"]
        assert all(
            item["module"] != "facebook-pages:CreatePostWithPhotos"
            for item in authorize["onerror"]
        )


def test_prepare_cli_writes_private_ignored_style_draft(tmp_path, capsys) -> None:
    source_path = tmp_path / "source.json"
    output_path = tmp_path / "import.json"
    source_path.write_text(json.dumps(source_blueprint()), encoding="utf-8")

    assert main(["--source", str(source_path), "--output", str(output_path)]) == 0
    assert "secret_scan=clear" in capsys.readouterr().out
    assert stat.S_IMODE(output_path.stat().st_mode) == 0o600
    assert validate_blueprint(json.loads(output_path.read_text(encoding="utf-8"))).errors == ()


def _all_modules(document: dict):
    def walk(flow):
        for module in flow:
            yield module
            for route in module.get("routes", []):
                yield from walk(route.get("flow", []))
            for handler in module.get("onerror", []):
                yield handler

    return list(walk(document["flow"]))
