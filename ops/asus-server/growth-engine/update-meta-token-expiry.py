#!/usr/bin/env python3
"""Read IG token expiry from Meta and update date-only fields in the server env file."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo


GRAPH_API_VERSION = "v27.0"
EXPECTED_APP_ID = "1679968647246378"
IG_TOKEN_VARIABLE = "GE_META_READ_TOKEN_IG_VENHO"
EXPIRY_VARIABLES = (
    "GE_META_TOKEN_EXPIRY_IG_VENHO",
    "GE_META_DATA_ACCESS_EXPIRY_IG_VENHO",
)
ENV_ASSIGNMENT = re.compile(r"^\s*([A-Z][A-Z0-9_]*)\s*=(.*)$")
ICT = ZoneInfo("Asia/Ho_Chi_Minh")


class MetaExpiryError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class GraphDebugTokenClient:
    def __init__(self, *, opener: Callable[..., Any] | None = None, timeout: float = 20.0) -> None:
        self._opener = opener or urllib.request.urlopen
        self._timeout = timeout

    def inspect(self, token: str) -> dict[str, Any]:
        query = urllib.parse.urlencode({"input_token": token, "access_token": token})
        url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/debug_token?{query}"
        request = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
        try:
            with self._opener(request, timeout=self._timeout) as response:
                body = response.read(1_000_001)
        except (urllib.error.URLError, TimeoutError, OSError):
            raise MetaExpiryError("ERR_GC2_META_DEBUG_REQUEST") from None
        except Exception:
            raise MetaExpiryError("ERR_GC2_META_DEBUG_REQUEST") from None
        if len(body) > 1_000_000:
            raise MetaExpiryError("ERR_GC2_META_DEBUG_RESPONSE_SIZE")
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise MetaExpiryError("ERR_GC2_META_DEBUG_RESPONSE") from None
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict) or "error" in payload:
            raise MetaExpiryError("ERR_GC2_META_DEBUG_REJECTED")
        return data


def expiry_dates(debug_data: dict[str, Any], *, expected_app_id: str = EXPECTED_APP_ID) -> dict[str, str]:
    if debug_data.get("app_id") != expected_app_id:
        raise MetaExpiryError("ERR_GC2_META_DEBUG_APP_MISMATCH")
    if debug_data.get("is_valid") is not True:
        raise MetaExpiryError("ERR_GC2_META_TOKEN_INVALID")
    token_timestamp = debug_data.get("expires_at")
    if token_timestamp is None or (type(token_timestamp) is int and token_timestamp == 0):
        token_expiry = "never"
    elif type(token_timestamp) is int and token_timestamp > 0:
        token_expiry = datetime.fromtimestamp(token_timestamp, timezone.utc).astimezone(ICT).date().isoformat()
    else:
        raise MetaExpiryError("ERR_GC2_META_EXPIRES_AT_INVALID")

    data_access_timestamp = debug_data.get("data_access_expires_at")
    if type(data_access_timestamp) is not int or data_access_timestamp <= 0:
        raise MetaExpiryError("ERR_GC2_META_DATA_ACCESS_EXPIRES_AT_MISSING")
    data_access_expiry = datetime.fromtimestamp(data_access_timestamp, timezone.utc).astimezone(ICT).date().isoformat()
    return {
        "GE_META_TOKEN_EXPIRY_IG_VENHO": token_expiry,
        "GE_META_DATA_ACCESS_EXPIRY_IG_VENHO": data_access_expiry,
    }


def read_env_file(path: Path) -> tuple[str, dict[str, str]]:
    if path.is_symlink() or not path.is_file():
        raise MetaExpiryError("ERR_GC2_META_ENV_FILE_INVALID")
    details = path.stat()
    if stat.S_IMODE(details.st_mode) != 0o600 or details.st_uid != os.geteuid():
        raise MetaExpiryError("ERR_GC2_META_ENV_FILE_PERMISSIONS")
    try:
        contents = path.read_text(encoding="utf-8")
    except OSError:
        raise MetaExpiryError("ERR_GC2_META_ENV_FILE_READ") from None
    values: dict[str, str] = {}
    for line in contents.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = ENV_ASSIGNMENT.match(line)
        if match:
            values[match.group(1)] = match.group(2).strip().strip("\"'")
    return contents, values


def replace_expiry_values(contents: str, updates: dict[str, str]) -> str:
    if set(updates) != set(EXPIRY_VARIABLES):
        raise MetaExpiryError("ERR_GC2_META_EXPIRY_UPDATE_FIELDS")
    output: list[str] = []
    seen: set[str] = set()
    for line in contents.splitlines(keepends=True):
        match = ENV_ASSIGNMENT.match(line.rstrip("\r\n"))
        name = match.group(1) if match else None
        if name not in updates:
            output.append(line)
            continue
        if name in seen:
            continue
        newline = "\r\n" if line.endswith("\r\n") else "\n"
        output.append(f"{name}={updates[name]}{newline}")
        seen.add(name)
    if output and not output[-1].endswith(("\n", "\r")):
        output[-1] += "\n"
    for name in EXPIRY_VARIABLES:
        if name not in seen:
            output.append(f"{name}={updates[name]}\n")
    return "".join(output)


def atomic_write_env(path: Path, contents: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise MetaExpiryError("ERR_GC2_META_ENV_FILE_INVALID")
    if stat.S_IMODE(path.stat().st_mode) != 0o600 or path.stat().st_uid != os.geteuid():
        raise MetaExpiryError("ERR_GC2_META_ENV_FILE_PERMISSIONS")
    descriptor, temporary_name = tempfile.mkstemp(prefix=".growth-engine.env.", dir=path.parent)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as target:
            target.write(contents)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary_name, path)
        os.chmod(path, 0o600)
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise MetaExpiryError("ERR_GC2_META_ENV_FILE_WRITE") from None


def update_expiry(path: Path, *, client: GraphDebugTokenClient | None = None) -> dict[str, str]:
    original, values = read_env_file(path)
    token = values.get(IG_TOKEN_VARIABLE, "").strip()
    if not token:
        raise MetaExpiryError("ERR_GC2_META_IG_TOKEN_MISSING")
    updates = expiry_dates((client or GraphDebugTokenClient()).inspect(token))
    changed = replace_expiry_values(original, updates)
    atomic_write_env(path, changed)
    check, check_values = read_env_file(path)
    if check != changed or any(check_values.get(name) != value for name, value in updates.items()):
        raise MetaExpiryError("ERR_GC2_META_ENV_FILE_VERIFY")
    return updates


def main(argv: list[str] | None = None, *, client: GraphDebugTokenClient | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env",
        type=Path,
        default=Path.home() / "venho/secrets/growth-engine.env",
        help="Server environment file (default is production).",
    )
    args = parser.parse_args(argv)
    try:
        updates = update_expiry(args.env, client=client)
    except MetaExpiryError as error:
        print(f"META_EXPIRY_UPDATE=ERROR code={error.code}")
        return 1
    except Exception:
        print("META_EXPIRY_UPDATE=ERROR code=ERR_GC2_META_EXPIRY_UNEXPECTED")
        return 1
    print("META_EXPIRY_UPDATE=PASS")
    for name in EXPIRY_VARIABLES:
        print(f"{name}={updates[name]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
