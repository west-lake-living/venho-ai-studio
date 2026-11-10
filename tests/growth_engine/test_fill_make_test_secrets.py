from __future__ import annotations

import importlib.util
import json
import stat
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts/growth_engine/fill_make_test_secrets.py"
SPEC = importlib.util.spec_from_file_location("fill_make_test_secrets", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
FILLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FILLER)

FAKE_BEARERS = {
    "GE_TEST_BEARER_FB_HANOI": "fake_hanoi_bearer_0123456789_abcdefghijklmnopqrstuvwxyz",
    "GE_TEST_BEARER_FB_VENHO": "fake_venho_bearer_0123456789_abcdefghijklmnopqrstuvwxyz",
    "GE_TEST_BEARER_IG": "fake_ig_bearer_0123456789_abcdefghijklmnopqrstuvwxyz",
}
FAKE_ACCESS_ID = "fake-access-client-id-value"
FAKE_ACCESS_SECRET = "fake-access-client-secret-value"


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


def _route(
    channel: str,
    media_id: int,
    authorize_id: int,
    post_id: int,
    receipt_id: int,
    app: str,
    marker: str,
) -> dict:
    error_receipt_id = receipt_id + 100
    return {
        "flow": [
            {
                "id": media_id,
                "module": "http:DownloadFile" if channel != "ig_venho" else "http:MakeRequest",
                "filter": {
                    "name": channel,
                    "conditions": [[{"a": "{{2.channel_key}}", "o": "text:equal", "b": channel}]],
                },
                "mapper": {"url": "{{2.media_url}}"},
            },
            _internal(authorize_id, marker, "executions/authorize"),
            {
                "id": post_id,
                "module": app,
                "mapper": {},
                "onerror": [
                    {
                        "flow": [
                            _internal(error_receipt_id, marker, "receipts"),
                            {"id": error_receipt_id + 1, "module": "builtin:Ignore", "mapper": {}},
                        ]
                    }
                ],
            },
            _internal(receipt_id, marker, "receipts"),
        ]
    }


def _blueprint() -> dict:
    return {
        "name": "Synthetic TEST blueprint",
        "flow": [
            {"id": 2, "module": "gateway:CustomWebHook", "mapper": {}},
            {
                "id": 5,
                "module": "builtin:BasicRouter",
                "mapper": {},
                "routes": [
                    _route(
                        "fb_hanoi", 4, 16, 3, 17, "facebook-pages:CreatePostWithPhotos",
                        "__SET_IN_MAKE_BEARER_FB_HANOI__",
                    ),
                    _route(
                        "ig_venho", 25, 26, 6, 27, "instagram-business:CreatePostPhoto",
                        "__SET_IN_MAKE_BEARER_IG_VENHO__",
                    ),
                    _route(
                        "fb_venho", 20, 21, 12, 22, "facebook-pages:CreatePostWithPhotos",
                        "__SET_IN_MAKE_BEARER_FB_VENHO__",
                    ),
                ],
            },
        ],
    }


def _handoff(path: Path) -> None:
    path.write_text(
        "# synthetic credentials for tests only\n"
        + "".join(f"{name}={value}\n" for name, value in FAKE_BEARERS.items()),
        encoding="utf-8",
    )
    path.chmod(0o600)


def _header(module: dict, name: str) -> str:
    matches = [
        header["value"]
        for header in module["mapper"]["headers"]
        if header["name"].casefold() == name.casefold()
    ]
    assert len(matches) == 1
    return matches[0]


def test_fill_document_replaces_per_route_credentials_and_all_internal_access_headers() -> None:
    filled, counts = FILLER.fill_document(
        _blueprint(),
        FAKE_BEARERS,
        FAKE_ACCESS_ID,
        FAKE_ACCESS_SECRET,
    )

    routes = filled["flow"][1]["routes"]
    for route in routes:
        channel = route["flow"][0]["filter"]["name"]
        variable = next(name for name, mapped_channel in FILLER.BEARER_VARIABLES.items() if mapped_channel == channel)
        expected_bearer = FAKE_BEARERS[variable]
        for module in FILLER._walk_modules(route["flow"]):
            mapper = module.get("mapper", {})
            if module.get("module") != "http:MakeRequest" or "/internal/" not in mapper.get("url", ""):
                continue
            assert _header(module, "Authorization") == f"Bearer {expected_bearer}"
            assert _header(module, "CF-Access-Client-Id") == FAKE_ACCESS_ID
            assert _header(module, "CF-Access-Client-Secret") == FAKE_ACCESS_SECRET
            assert module["mapper"]["url"].startswith("https://ge-test.venhohotel.com/internal/")

    assert counts == {
        "bearer_fb_hanoi": 3,
        "bearer_fb_venho": 3,
        "bearer_ig_venho": 3,
        "access_client_id": 9,
        "access_client_secret": 9,
        "base_url": 9,
    }
    assert all("__SET_IN_MAKE_" not in value for value in FILLER._all_strings(filled))
    assert all("set-in-make.invalid" not in value for value in FILLER._all_strings(filled))


def test_fill_document_rejects_bearer_assigned_to_wrong_route() -> None:
    document = _blueprint()
    document["flow"][1]["routes"][0]["flow"][1]["mapper"]["headers"][0]["value"] = (
        "Bearer __SET_IN_MAKE_BEARER_FB_VENHO__"
    )

    with pytest.raises(FILLER.FillError, match="route_bearer_placeholder_mismatch"):
        FILLER.fill_document(document, FAKE_BEARERS, FAKE_ACCESS_ID, FAKE_ACCESS_SECRET)


def test_bearer_handoff_must_be_mode_600_and_complete(tmp_path: Path) -> None:
    handoff = tmp_path / "growth-engine-test.make-bearers.tmp"
    _handoff(handoff)
    assert FILLER.load_bearer_handoff(handoff) == FAKE_BEARERS

    handoff.chmod(0o640)
    with pytest.raises(FILLER.FillError, match="bearer_handoff_must_be_mode_600"):
        FILLER.load_bearer_handoff(handoff)


def test_cli_writes_mode_600_output_and_prints_counts_only(tmp_path: Path, monkeypatch, capsys) -> None:
    incoming = tmp_path / "_incoming"
    incoming.mkdir()
    blueprint = incoming / "make_test_import.json"
    blueprint.write_text(json.dumps(_blueprint()), encoding="utf-8")
    handoff = incoming / "growth-engine-test.make-bearers.tmp"
    _handoff(handoff)
    output = incoming / "make_test_import.secret.json"
    fake_credentials = iter([FAKE_ACCESS_ID, FAKE_ACCESS_SECRET])
    monkeypatch.setattr(FILLER.getpass, "getpass", lambda _prompt: next(fake_credentials))
    monkeypatch.chdir(tmp_path)

    exit_code = FILLER.main([])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    assert "base_url=9" in captured.out
    assert "bearer_fb_hanoi=3" in captured.out
    for secret in (*FAKE_BEARERS.values(), FAKE_ACCESS_ID, FAKE_ACCESS_SECRET):
        assert secret not in captured.out
        assert secret not in captured.err


def test_gitignore_covers_secret_blueprint_and_bearer_handoff() -> None:
    gitignore = SCRIPT.parents[2] / ".gitignore"
    rules = gitignore.read_text(encoding="utf-8").splitlines()

    assert "/_incoming/*.secret.json" in rules
    assert "*.make-bearers.tmp" in rules
