from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse


_SCRIPT = Path("ops/asus-server/growth-engine/update-meta-token-expiry.py")
_SPEC = importlib.util.spec_from_file_location("update_meta_token_expiry", _SCRIPT)
assert _SPEC and _SPEC.loader
update_meta = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = update_meta
_SPEC.loader.exec_module(update_meta)


TOKEN = "EAA_TEST_TOKEN_SHOULD_NEVER_PRINT"


class _Response:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self, _limit: int) -> bytes:
        return self.body


def _timestamp(year: int, month: int, day: int) -> int:
    return int(datetime(year, month, day, 12, tzinfo=timezone.utc).timestamp())


def _debug_payload(**overrides):
    data = {
        "app_id": update_meta.EXPECTED_APP_ID,
        "is_valid": True,
        "expires_at": _timestamp(2027, 1, 10),
        "data_access_expires_at": _timestamp(2027, 2, 9),
    }
    data.update(overrides)
    return json.dumps({"data": data}).encode()


def _env_file(tmp_path: Path) -> Path:
    path = tmp_path / "growth-engine.env"
    path.write_text(f"GE_META_READ_TOKEN_IG_VENHO={TOKEN}\nGE_ENV=production\n", encoding="utf-8")
    path.chmod(0o600)
    return path


def test_graph_debug_token_uses_server_token_and_returns_no_token_text() -> None:
    captured = {}

    def opener(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        return _Response(_debug_payload())

    data = update_meta.GraphDebugTokenClient(opener=opener).inspect(TOKEN)
    params = parse_qs(urlparse(captured["url"]).query)

    assert params == {"input_token": [TOKEN], "access_token": [TOKEN]}
    assert "/v27.0/debug_token" in captured["url"]
    assert data["app_id"] == update_meta.EXPECTED_APP_ID


def test_expiry_update_writes_dates_atomically_without_echoing_token(tmp_path: Path, capsys) -> None:
    path = _env_file(tmp_path)

    class Client:
        def inspect(self, token):
            assert token == TOKEN
            return json.loads(_debug_payload())["data"]

    result = update_meta.main(["--env", str(path)], client=Client())
    output = capsys.readouterr()
    contents = path.read_text(encoding="utf-8")

    assert result == 0
    assert "META_EXPIRY_UPDATE=PASS" in output.out
    assert "GE_META_TOKEN_EXPIRY_IG_VENHO=2027-01-10" in output.out
    assert "GE_META_DATA_ACCESS_EXPIRY_IG_VENHO=2027-02-09" in output.out
    assert TOKEN not in output.out + output.err
    assert f"GE_META_READ_TOKEN_IG_VENHO={TOKEN}" in contents
    assert "GE_ENV=production" in contents
    assert "GE_META_TOKEN_EXPIRY_IG_VENHO=2027-01-10" in contents
    assert "GE_META_DATA_ACCESS_EXPIRY_IG_VENHO=2027-02-09" in contents
    assert os.stat(path).st_mode & 0o777 == 0o600


def test_meta_update_rejects_wrong_app_or_non_expiring_fields_without_change(tmp_path: Path) -> None:
    path = _env_file(tmp_path)
    original = path.read_text(encoding="utf-8")
    for payload in (
        _debug_payload(app_id="wrong-app"),
        _debug_payload(is_valid=False),
        _debug_payload(expires_at=0),
    ):
        class Client:
            def inspect(self, _token):
                return json.loads(payload)["data"]

        try:
            update_meta.update_expiry(path, client=Client())
        except update_meta.MetaExpiryError:
            pass
        else:
            raise AssertionError("invalid Meta debug response was accepted")
        assert path.read_text(encoding="utf-8") == original


def test_meta_request_failure_does_not_echo_url_or_token(tmp_path: Path, capsys) -> None:
    path = _env_file(tmp_path)

    def opener(_request, timeout):
        raise OSError(f"failed URL with {TOKEN}")

    result = update_meta.main(
        ["--env", str(path)],
        client=update_meta.GraphDebugTokenClient(opener=opener),
    )
    output = capsys.readouterr()

    assert result == 1
    assert "ERR_GC2_META_DEBUG_REQUEST" in output.out
    assert TOKEN not in output.out + output.err
