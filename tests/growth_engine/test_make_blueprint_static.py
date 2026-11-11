from __future__ import annotations

import json

import pytest

from scripts.growth_engine.check_make_blueprint import main, validate_blueprint


def valid_blueprint() -> dict:
    return {
        "name": "synthetic",
        "metadata": {"instant": True, "scenario": {"sequential": True}},
        "flow": [
            {"id": 2, "module": "gateway:CustomWebHook", "mapper": {}},
            {
                "id": 5,
                "module": "builtin:BasicRouter",
                "routes": [
                    {
                        "flow": [
                            {
                                "id": 14,
                                "module": "http:MakeRequest",
                                "mapper": {
                                    "url": "https://__SET_IN_MAKE_BASE_URL_TEST__/internal",
                                    "method": "post",
                                    "headers": [
                                        {
                                            "name": "Authorization",
                                            "value": "Bearer __SET_IN_MAKE_BEARER_FB_HANOI__",
                                        }
                                    ],
                                    "body": "{{2.command_token}}",
                                },
                            },
                        ]
                    }
                ],
            },
        ],
    }


def test_accepts_unique_ids_prior_mappings_and_placeholder_credentials() -> None:
    result = validate_blueprint(valid_blueprint())

    assert result.errors == ()
    assert result.module_count == 3
    assert result.route_count == 1
    assert result.mapping_count == 1


def test_accepts_backticked_hyphenated_mapping_key() -> None:
    document = valid_blueprint()
    request = document["flow"][1]["routes"][0]["flow"][0]
    request["mapper"]["body"] = "{{2.headers.`content-type`}}"

    assert "mapping_hyphen_must_be_backticked" not in validate_blueprint(document).errors


def test_rejects_unquoted_hyphenated_mapping_key() -> None:
    document = valid_blueprint()
    request = document["flow"][1]["routes"][0]["flow"][0]
    request["mapper"]["body"] = "{{2.headers.content-type}}"

    assert "mapping_hyphen_must_be_backticked" in validate_blueprint(document).errors


def test_accepts_reserved_invalid_placeholder_host() -> None:
    document = valid_blueprint()
    document["flow"][1]["routes"][0]["flow"][0]["mapper"]["url"] = (
        "https://set-in-make.invalid/internal/growth/v2/receipts"
    )

    assert validate_blueprint(document).errors == ()


def test_rejects_duplicate_ids() -> None:
    document = valid_blueprint()
    document["flow"].append({"id": 2, "module": "gateway:WebhookRespond"})

    assert "duplicate_module_id" in validate_blueprint(document).errors


def test_rejects_missing_or_forward_mapping_source() -> None:
    document = valid_blueprint()
    document["flow"][0]["mapper"] = {"payload": "{{15.data}}"}

    assert "mapping_source_missing_or_forward" in validate_blueprint(document).errors


def test_rejects_http_request_with_empty_method() -> None:
    document = valid_blueprint()
    request = document["flow"][1]["routes"][0]["flow"][0]
    request["mapper"]["method"] = ""

    assert "http_request_method_missing" in validate_blueprint(document).errors


def test_rejects_http_method_with_noncanonical_case() -> None:
    document = valid_blueprint()
    request = document["flow"][1]["routes"][0]["flow"][0]
    request["mapper"]["method"] = "POST"

    assert "http_request_method_invalid_case" in validate_blueprint(document).errors


def test_rejects_scheduled_scenario_instead_of_immediate_webhook() -> None:
    document = valid_blueprint()
    document["metadata"]["instant"] = False

    assert "scenario_not_immediate" in validate_blueprint(document).errors


def test_rejects_webhook_responder_with_sequential_processing() -> None:
    document = valid_blueprint()
    document["flow"][1]["routes"][0]["flow"].append(
        {"id": 15, "module": "gateway:WebhookRespond", "mapper": {"body": "ack"}}
    )

    assert "webhook_response_not_supported_with_sequential_processing" in validate_blueprint(document).errors


@pytest.mark.parametrize(
    ("module_type", "mapper"),
    [
        ("http:DownloadFile", {"url": "{{2.media_url}}"}),
        ("http:MakeRequest", {"url": "{{2.media_url}}", "method": "get"}),
    ],
)
def test_media_fetch_requires_ignore_error_handler(module_type: str, mapper: dict) -> None:
    document = valid_blueprint()
    route_flow = document["flow"][1]["routes"][0]["flow"]
    fetch = {"id": 10, "module": module_type, "mapper": mapper}
    ignore = {"id": 11, "module": "builtin:Ignore", "mapper": {}}
    fetch["onerror"] = [ignore]
    route_flow.insert(0, fetch)

    assert "media_fetch_error_must_terminate_with_ignore" not in validate_blueprint(document).errors

    fetch.pop("onerror")
    assert "media_fetch_error_must_terminate_with_ignore" in validate_blueprint(document).errors


def test_authorize_request_requires_ignore_error_handler() -> None:
    document = valid_blueprint()
    request = document["flow"][1]["routes"][0]["flow"][0]
    request["mapper"]["url"] = "https://set-in-make.invalid/internal/growth/v2/executions/authorize"
    request["onerror"] = [{"id": 16, "module": "builtin:Ignore", "mapper": {}}]

    assert "authorize_error_must_terminate_with_ignore" not in validate_blueprint(document).errors

    request.pop("onerror")
    assert "authorize_error_must_terminate_with_ignore" in validate_blueprint(document).errors


def test_rejects_facebook_post_id_alias_when_module_output_is_id() -> None:
    document = valid_blueprint()
    route_flow = document["flow"][1]["routes"][0]["flow"]
    route_flow.insert(0, {"id": 3, "module": "facebook-pages:CreatePostWithPhotos", "mapper": {}})
    route_flow[1]["mapper"]["jsonStringBodyContent"] = '{"platform_post_id":"{{3.post_id}}"}'

    assert "facebook_receipt_must_use_module_id" in validate_blueprint(document).errors


def test_rejects_real_url_and_token_like_literal_without_echoing_values() -> None:
    document = valid_blueprint()
    document["flow"][1]["routes"][0]["flow"][0]["mapper"]["url"] = (
        "https://example.invalid/path?access_token=privatevalue"
    )
    result = validate_blueprint(document)

    assert "literal_url" in result.errors
    assert "signed_url_value" in result.errors
    assert "privatevalue" not in json.dumps(result.__dict__)


def test_cli_parses_blueprint_json(tmp_path, capsys) -> None:
    path = tmp_path / "blueprint.json"
    path.write_text(json.dumps(valid_blueprint()), encoding="utf-8")

    assert main([str(path)]) == 0
    assert "PASS: static check" in capsys.readouterr().out


def test_cli_reports_invalid_json_without_echoing_contents(tmp_path, capsys) -> None:
    path = tmp_path / "invalid.json"
    path.write_text("privatevalue", encoding="utf-8")

    assert main([str(path)]) == 2
    output = capsys.readouterr().out
    assert output == "FAIL: blueprint unavailable or invalid JSON\n"
    assert "privatevalue" not in output
