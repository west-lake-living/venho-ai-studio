from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import pytest


_SCRIPT = Path("ops/asus-server/growth-engine/push-meta-tokens.py")
_SPEC = importlib.util.spec_from_file_location("push_meta_tokens", _SCRIPT)
assert _SPEC and _SPEC.loader
push_meta_tokens = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = push_meta_tokens
_SPEC.loader.exec_module(push_meta_tokens)


def _fake_value(prefix: str, letter: str) -> str:
    return prefix + letter * 40


USER_TOKEN = _fake_value("TEST_ONLY_USER_", "u")
HANOI_TOKEN = _fake_value("TEST_ONLY_PAGE_A_", "a")
VENHO_TOKEN = _fake_value("TEST_ONLY_PAGE_B_", "b")


class FakeGraphClient:
    def __init__(self, rows: Sequence[Mapping[str, Any]]) -> None:
        self.rows = rows
        self.user_token = None

    def get_accounts(self, user_token: str) -> Sequence[Mapping[str, Any]]:
        self.user_token = user_token
        return self.rows


class FakeResponse:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit: int) -> bytes:
        return self.body


class FakeSshTransport:
    def __init__(self, home: Path, initial_env: str) -> None:
        self.home = home
        self.env_path = home / "venho" / "secrets" / "growth-engine.env"
        self.env_path.parent.mkdir(parents=True)
        self.env_path.write_text(initial_env, encoding="utf-8")
        self.calls: list[tuple[str, dict[str, str]]] = []

    def update_tokens(self, host: str, tokens: Mapping[str, str]) -> Sequence[str]:
        self.calls.append((host, dict(tokens)))
        fake_stdin = io.StringIO(json.dumps(dict(tokens)))
        fake_stdout = io.StringIO()
        namespace: dict[str, Any] = {"__name__": "__main__"}
        with contextlib.ExitStack() as stack:
            stack.enter_context(contextlib.redirect_stdout(fake_stdout))
            stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
            stack.enter_context(patch("sys.stdin", fake_stdin))
            stack.enter_context(patch.object(Path, "home", return_value=self.home))
            try:
                exec(push_meta_tokens._REMOTE_UPDATE_SCRIPT, namespace)
            except SystemExit as error:
                assert error.code == 0
        return fake_stdout.getvalue().splitlines()


def _accounts() -> list[dict[str, str]]:
    # Names deliberately conflict with IDs; the implementation must select by ID.
    return [
        {"id": "1124616474074140", "name": "Ven Hồ Hotel", "access_token": HANOI_TOKEN},
        {"id": "803531149684177", "name": "Ven Hồ Hotel Hanoi", "access_token": VENHO_TOKEN},
    ]


def test_cli_selects_by_page_id_and_updates_only_meta_token_lines(tmp_path, capsys) -> None:
    graph = FakeGraphClient(_accounts())
    initial = (
        "GE_ENV=production\n"
        "GE_META_READ_TOKEN_PAGE_A=old-a\n"
        "KEEP_THIS=unchanged\n"
        "GE_META_READ_TOKEN_FB_HANOI=old-a\n"
        "GE_META_READ_TOKEN_PAGE_B=old-b\n"
        "GE_META_READ_TOKEN_FB_VENHO=old-b\n"
        "GE_META_READ_TOKEN_IG_VENHO=old-ig\n"
    )
    ssh = FakeSshTransport(tmp_path, initial)

    result = push_meta_tokens.main(
        ["--host", "fake-server"],
        graph_client=graph,
        ssh_transport=ssh,
        token_prompt=lambda: USER_TOKEN,
    )

    output = capsys.readouterr()
    assert result == 0
    assert output.err == ""
    assert "KEEP_THIS=unchanged\n" in ssh.env_path.read_text(encoding="utf-8")
    env_text = ssh.env_path.read_text(encoding="utf-8")
    for name, token in (
        ("GE_META_READ_TOKEN_PAGE_A", HANOI_TOKEN),
        ("GE_META_READ_TOKEN_FB_HANOI", HANOI_TOKEN),
        ("GE_META_READ_TOKEN_PAGE_B", VENHO_TOKEN),
        ("GE_META_READ_TOKEN_FB_VENHO", VENHO_TOKEN),
        ("GE_META_READ_TOKEN_IG_VENHO", USER_TOKEN),
    ):
        assert f"{name}={token}\n" in env_text
    assert ssh.env_path.stat().st_mode & 0o777 == 0o600
    assert graph.user_token == USER_TOKEN
    assert ssh.calls[0][0] == "fake-server"
    assert USER_TOKEN not in output.out and HANOI_TOKEN not in output.out and VENHO_TOKEN not in output.out
    assert "GE_META_READ_TOKEN_PAGE_A DA_DAT" in output.out
    assert "GE_META_READ_TOKEN_PAGE_A DA_CO_GIA_TRI" in output.out


def test_cli_is_idempotent_and_preserves_unrelated_lines(tmp_path, capsys) -> None:
    ssh = FakeSshTransport(
        tmp_path,
        "KEEP=first\nGE_META_READ_TOKEN_PAGE_A=old\nKEEP=second\nGE_META_READ_TOKEN_PAGE_A=duplicate\n",
    )
    graph = FakeGraphClient(_accounts())

    assert push_meta_tokens.main([], graph_client=graph, ssh_transport=ssh, token_prompt=lambda: USER_TOKEN) == 0
    after_first = ssh.env_path.read_text(encoding="utf-8")
    assert push_meta_tokens.main([], graph_client=graph, ssh_transport=ssh, token_prompt=lambda: USER_TOKEN) == 0
    after_second = ssh.env_path.read_text(encoding="utf-8")

    assert after_second == after_first
    assert after_second.count("GE_META_READ_TOKEN_PAGE_A=") == 1
    assert after_second.startswith("KEEP=first\nGE_META_READ_TOKEN_PAGE_A=")
    assert "KEEP=second\n" in after_second
    output = capsys.readouterr()
    assert USER_TOKEN not in output.out and HANOI_TOKEN not in output.out and VENHO_TOKEN not in output.out


def test_missing_or_mismatched_page_ids_abort_before_ssh(capsys) -> None:
    graph = FakeGraphClient(
        [
            {"id": "wrong-id", "name": "Ven Hồ Hotel Hanoi", "access_token": HANOI_TOKEN},
            {"id": "803531149684177", "name": "Ven Hồ Hotel", "access_token": VENHO_TOKEN},
        ]
    )
    ssh = _NoWriteSshTransport()

    result = push_meta_tokens.main([], graph_client=graph, ssh_transport=ssh, token_prompt=lambda: USER_TOKEN)

    output = capsys.readouterr()
    assert result == 1
    assert ssh.calls == 0
    assert output.err == ""
    assert output.out.splitlines() == [f"{name} ERROR" for name in push_meta_tokens.TOKEN_VARIABLES]
    assert USER_TOKEN not in output.out and HANOI_TOKEN not in output.out and VENHO_TOKEN not in output.out


class _NoWriteSshTransport:
    def __init__(self) -> None:
        self.calls = 0

    def update_tokens(self, host: str, tokens: Mapping[str, str]) -> Sequence[str]:
        self.calls += 1
        raise AssertionError("missing Page must stop before SSH")


def test_graph_client_uses_only_configured_v27_accounts_request() -> None:
    captured = {}

    def fake_opener(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        return FakeResponse(json.dumps({"data": _accounts()}).encode("utf-8"))

    result = push_meta_tokens.GraphApiClient(opener=fake_opener).get_accounts(USER_TOKEN)
    parsed = urlsplit(captured["url"])
    query = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.netloc == "graph.facebook.com"
    assert parsed.path == "/v27.0/me/accounts"
    assert query["fields"] == ["id,name,access_token"]
    assert query["access_token"] == [USER_TOKEN]
    assert len(result) == 2
