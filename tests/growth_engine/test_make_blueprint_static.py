from __future__ import annotations

import json

from scripts.growth_engine.check_make_blueprint import main, validate_blueprint


def valid_blueprint() -> dict:
    return {
        "name": "synthetic",
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
                                "module": "http:ActionSendData",
                                "mapper": {
                                    "url": "https://__SET_IN_MAKE_BASE_URL_TEST__/internal",
                                    "headers": [
                                        {
                                            "name": "Authorization",
                                            "value": "Bearer __SET_IN_MAKE_BEARER_FB_HANOI__",
                                        }
                                    ],
                                    "body": "{{2.command_token}}",
                                },
                            },
                            {
                                "id": 15,
                                "module": "gateway:WebhookRespond",
                                "mapper": {"body": "{{14.data.id}}"},
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
    assert result.module_count == 4
    assert result.route_count == 1
    assert result.mapping_count == 2


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
