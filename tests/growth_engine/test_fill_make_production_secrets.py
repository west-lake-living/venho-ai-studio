from __future__ import annotations

import importlib.util
import json
import stat
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts/growth_engine/fill_make_production_secrets.py"
SPEC = importlib.util.spec_from_file_location("fill_make_production_secrets", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
FILLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FILLER)

FAKE_BEARERS = {
    "GE_MAKE_BEARER_FB_HANOI": "production_fake_hanoi_0123456789_abcdefghijklmnopqrstuvwxyz",
    "GE_MAKE_BEARER_FB_VENHO": "production_fake_venho_0123456789_abcdefghijklmnopqrstuvwxyz",
    "GE_MAKE_BEARER_IG_VENHO": "production_fake_ig_0123456789_abcdefghijklmnopqrstuvwxyz",
}
FAKE_ACCESS_ID = "fake-production-access-id"
FAKE_ACCESS_SECRET = "fake-production-access-secret"


def _internal(module_id: int, bearer_marker: str, endpoint: str) -> dict:
    return {
        "id": module_id,
        "module": "http:MakeRequest",
        "mapper": {
            "method": "post",
            "url": f"https://set-in-make.invalid/internal/growth/v2/{endpoint}",
            "headers": [
                {"name": "Authorization", "value": f"Bearer {bearer_marker}"},
                {"name": "CF-Access-Client-Id", "value": "__SET_IN_MAKE_ACCESS_CLIENT_ID__"},
                {"name": "CF-Access-Client-Secret", "value": "__SET_IN_MAKE_ACCESS_CLIENT_SECRET__"},
            ],
        },
    }


def _route(channel: str, first_id: int, marker: str) -> dict:
    return {
        "flow": [
            {
                "id": first_id,
                "module": "http:DownloadFile",
                "filter": {
                    "name": channel,
                    "conditions": [[{
                        "a": "{{2.channel_key}}",
                        "o": "text:equal",
                        "b": channel,
                    }]],
                },
                "mapper": {"url": "{{2.media_url}}"},
            },
            _internal(first_id + 1, marker, "executions/authorize"),
            {
                "id": first_id + 2,
                "module": "facebook-pages:CreatePostWithPhotos" if channel != "ig_venho"
                else "instagram-business:CreatePostPhoto",
                "mapper": {},
            },
            _internal(first_id + 3, marker, "receipts"),
            _internal(first_id + 4, marker, "receipts"),
        ]
    }


def _blueprint() -> dict:
    return {
        "metadata": {"instant": True, "scenario": {"sequential": True}},
        "flow": [
            {"id": 2, "module": "gateway:CustomWebHook", "mapper": {}},
            {
                "id": 5,
                "module": "builtin:BasicRouter",
                "mapper": {},
                "filter": {
                    "name": "v2 production common",
                    "conditions": [[
                        {"a": "{{2.schema_version}}", "o": "text:equal", "b": "growth.command.v2"},
                        {"a": "{{2.environment}}", "o": "text:equal", "b": "production"},
                    ]],
                },
                "routes": [
                    _route("fb_hanoi", 14, "__SET_IN_MAKE_BEARER_FB_HANOI__"),
                    _route("ig_venho", 24, "__SET_IN_MAKE_BEARER_IG_VENHO__"),
                    _route("fb_venho", 34, "__SET_IN_MAKE_BEARER_FB_VENHO__"),
                ],
            },
        ],
    }


def _write_handoff(path: Path) -> None:
    path.write_text("".join(f"{name}={value}\n" for name, value in FAKE_BEARERS.items()), encoding="utf-8")
    path.chmod(0o600)


def _header(module: dict, name: str) -> str:
    matches = [item["value"] for item in module["mapper"]["headers"] if item["name"].casefold() == name.casefold()]
    assert len(matches) == 1
    return matches[0]


def test_fills_production_base_and_route_credentials_without_placeholders() -> None:
    document, counts = FILLER.fill_production_document(
        _blueprint(), FAKE_BEARERS, FAKE_ACCESS_ID, FAKE_ACCESS_SECRET
    )

    assert counts == {
        "bearer_fb_hanoi": 3,
        "bearer_fb_venho": 3,
        "bearer_ig_venho": 3,
        "access_client_id": 9,
        "access_client_secret": 9,
        "base_url": 9,
    }
    for route in document["flow"][1]["routes"]:
        channel = route["flow"][0]["filter"]["name"]
        prod_variable = next(key for key, marker in {
            "GE_MAKE_BEARER_FB_HANOI": "fb_hanoi",
            "GE_MAKE_BEARER_FB_VENHO": "fb_venho",
            "GE_MAKE_BEARER_IG_VENHO": "ig_venho",
        }.items() if marker == channel)
        expected_bearer = FAKE_BEARERS[prod_variable]
        for module in FILLER.shared._walk_modules(route["flow"]):
            if module.get("module") != "http:MakeRequest":
                continue
            assert module["mapper"]["url"].startswith("https://growth-api.venhohotel.com/internal/")
            assert _header(module, "Authorization") == f"Bearer {expected_bearer}"
            assert _header(module, "CF-Access-Client-Id") == FAKE_ACCESS_ID
            assert _header(module, "CF-Access-Client-Secret") == FAKE_ACCESS_SECRET

    all_strings = list(FILLER.shared._all_strings(document))
    assert all("__SET_IN_MAKE_" not in value for value in all_strings)
    assert all("set-in-make.invalid" not in value for value in all_strings)


def test_requires_production_common_filter_and_rejects_test_filter() -> None:
    document = _blueprint()
    document["flow"][1]["filter"]["conditions"][0][1]["b"] = "test"

    with pytest.raises(FILLER.ProductionFillError, match="production_common_filter_invalid"):
        FILLER.fill_production_document(document, FAKE_BEARERS, FAKE_ACCESS_ID, FAKE_ACCESS_SECRET)


def test_cli_writes_mode_600_and_never_prints_secrets(tmp_path: Path, monkeypatch, capsys) -> None:
    incoming = tmp_path / "_incoming"
    incoming.mkdir(mode=0o700)
    blueprint = incoming / "make_production_import.json"
    blueprint.write_text(json.dumps(_blueprint()), encoding="utf-8")
    blueprint.chmod(0o600)
    handoff = incoming / "growth-engine.make-bearers.tmp"
    _write_handoff(handoff)
    output = incoming / "make_production_import.secret.json"
    hidden = iter((FAKE_ACCESS_ID, FAKE_ACCESS_SECRET))
    monkeypatch.setattr(FILLER.getpass, "getpass", lambda _prompt: next(hidden))
    monkeypatch.chdir(tmp_path)

    assert FILLER.main([]) == 0
    captured = capsys.readouterr()

    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    assert "base_url=9" in captured.out
    for secret in (*FAKE_BEARERS.values(), FAKE_ACCESS_ID, FAKE_ACCESS_SECRET):
        assert secret not in captured.out
        assert secret not in captured.err
