#!/usr/bin/env python3
"""Push Meta read tokens to the GC2 server without echoing or storing input locally."""

from __future__ import annotations

import argparse
import getpass
import json
import re
import shlex
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Mapping, Optional, Protocol, Sequence


GRAPH_API_VERSION = "v27.0"
GRAPH_FIELDS = "id,name,access_token"
PAGE_TOKEN_VARIABLES = {
    "1124616474074140": ("GE_META_READ_TOKEN_PAGE_A", "GE_META_READ_TOKEN_FB_HANOI"),
    "803531149684177": ("GE_META_READ_TOKEN_PAGE_B", "GE_META_READ_TOKEN_FB_VENHO"),
}
TOKEN_VARIABLES = (
    "GE_META_READ_TOKEN_PAGE_A",
    "GE_META_READ_TOKEN_FB_HANOI",
    "GE_META_READ_TOKEN_PAGE_B",
    "GE_META_READ_TOKEN_FB_VENHO",
    "GE_META_READ_TOKEN_IG_VENHO",
)


class SafeUpdateError(RuntimeError):
    """Failure type that deliberately carries no provider or secret text."""


class GraphClient(Protocol):
    def get_accounts(self, user_token: str) -> Sequence[Mapping[str, Any]]: ...


class SshTransport(Protocol):
    def update_tokens(self, host: str, tokens: Mapping[str, str]) -> Sequence[str]: ...


class GraphApiClient:
    """Minimal standard-library client for the configured read-only Graph call."""

    def __init__(self, *, opener: Any = None, timeout: float = 20.0) -> None:
        self._opener = opener or urllib.request.urlopen
        self._timeout = timeout

    def get_accounts(self, user_token: str) -> Sequence[Mapping[str, Any]]:
        token = user_token.strip()
        if not token:
            raise SafeUpdateError("graph request failed")
        query = urllib.parse.urlencode({"fields": GRAPH_FIELDS, "access_token": token})
        url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/me/accounts?{query}"
        request = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
        try:
            with self._opener(request, timeout=self._timeout) as response:
                body = response.read(2_000_001)
        except urllib.error.HTTPError as error:
            # Do not include the exception: its URL can contain the user token.
            raise SafeUpdateError("graph request failed") from None
        except Exception:
            raise SafeUpdateError("graph request failed") from None
        if len(body) > 2_000_000:
            raise SafeUpdateError("graph response invalid")
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise SafeUpdateError("graph response invalid") from None
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
            raise SafeUpdateError("graph response invalid")
        return data


def resolve_meta_tokens(
    accounts: Sequence[Mapping[str, Any]], user_token: str
) -> dict[str, str]:
    """Resolve exact Page IDs; never select using the display name."""
    found: dict[str, str] = {}
    for row in accounts:
        page_id = row.get("id")
        if not isinstance(page_id, str) or page_id not in PAGE_TOKEN_VARIABLES:
            continue
        page_token = row.get("access_token")
        if not isinstance(page_token, str) or not page_token.strip() or any(c in page_token for c in "\r\n\0"):
            continue
        for variable in PAGE_TOKEN_VARIABLES[page_id]:
            found[variable] = page_token

    normalized_user_token = user_token.strip()
    if not normalized_user_token or any(c in normalized_user_token for c in "\r\n\0"):
        raise SafeUpdateError("user token invalid")
    found["GE_META_READ_TOKEN_IG_VENHO"] = normalized_user_token
    missing = [name for name in TOKEN_VARIABLES if name not in found]
    if missing:
        raise SafeUpdateError("required Page token missing")
    return found


def replace_env_values(original: str, updates: Mapping[str, str]) -> str:
    """Pure helper mirrored by the remote writer; preserve every unrelated line."""
    if set(updates) != set(TOKEN_VARIABLES):
        raise ValueError("unexpected token variable set")
    for value in updates.values():
        if not isinstance(value, str) or not value.strip() or any(c in value for c in "\r\n\0"):
            raise ValueError("invalid one-line token value")

    assignment = re.compile(r"^\s*(GE_META_READ_TOKEN_[A-Z_]+)\s*=")
    output: list[str] = []
    seen: set[str] = set()
    for line in original.splitlines(keepends=True):
        match = assignment.match(line)
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
    for name in TOKEN_VARIABLES:
        if name not in seen:
            output.append(f"{name}={updates[name]}\n")
    return "".join(output)


_REMOTE_UPDATE_SCRIPT = r'''import json, os, re, sys, tempfile
from pathlib import Path
NAMES = (
    "GE_META_READ_TOKEN_PAGE_A", "GE_META_READ_TOKEN_FB_HANOI",
    "GE_META_READ_TOKEN_PAGE_B", "GE_META_READ_TOKEN_FB_VENHO",
    "GE_META_READ_TOKEN_IG_VENHO",
)
def emit(state):
    for name in NAMES:
        print(name, state)
def main():
    temp_path = None
    try:
        updates = json.load(sys.stdin)
        if not isinstance(updates, dict) or set(updates) != set(NAMES):
            raise ValueError
        for value in updates.values():
            if not isinstance(value, str) or not value.strip() or any(c in value for c in "\r\n\0"):
                raise ValueError
        path = Path.home() / "venho" / "secrets" / "growth-engine.env"
        if not path.is_file():
            raise ValueError
        original = path.read_text(encoding="utf-8")
        assignment = re.compile(r"^\s*(GE_META_READ_TOKEN_[A-Z_]+)\s*=")
        output, seen = [], set()
        for line in original.splitlines(keepends=True):
            match = assignment.match(line)
            name = match.group(1) if match else None
            if name not in updates:
                output.append(line)
                continue
            if name in seen:
                continue
            newline = "\r\n" if line.endswith("\r\n") else "\n"
            output.append(name + "=" + updates[name] + newline)
            seen.add(name)
        if output and not output[-1].endswith(("\n", "\r")):
            output[-1] += "\n"
        for name in NAMES:
            if name not in seen:
                output.append(name + "=" + updates[name] + "\n")
        fd, temp_path = tempfile.mkstemp(prefix=".growth-engine.env.", dir=str(path.parent))
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as target:
            target.write("".join(output))
            target.flush()
            os.fsync(target.fileno())
        os.replace(temp_path, path)
        temp_path = None
        os.chmod(path, 0o600)
        check = path.read_text(encoding="utf-8")
        values = {}
        for line in check.splitlines():
            match = assignment.match(line)
            if match:
                values[match.group(1)] = line.split("=", 1)[1]
        if any(values.get(name) != updates[name] for name in NAMES):
            raise ValueError
        emit("DA_CO_GIA_TRI")
        return 0
    except Exception:
        if temp_path:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
        emit("ERROR")
        return 1
raise SystemExit(main())
'''


class OpenSshTransport:
    def update_tokens(self, host: str, tokens: Mapping[str, str]) -> Sequence[str]:
        payload = json.dumps(dict(tokens), separators=(",", ":")).encode("utf-8")
        remote_command = "python3 -c " + shlex.quote(_REMOTE_UPDATE_SCRIPT)
        try:
            completed = subprocess.run(
                ["ssh", host, remote_command],
                input=payload,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=45,
            )
        except Exception:
            raise SafeUpdateError("server update failed") from None
        expected = [f"{name} DA_CO_GIA_TRI" for name in TOKEN_VARIABLES]
        try:
            lines = completed.stdout.decode("utf-8").splitlines()
        except UnicodeDecodeError:
            raise SafeUpdateError("server update failed") from None
        if completed.returncode != 0 or lines != expected:
            raise SafeUpdateError("server update failed")
        return lines


def _print_error(stream: Any = None) -> None:
    target = stream or sys.stdout
    for name in TOKEN_VARIABLES:
        print(name, "ERROR", file=target)


def main(
    argv: Optional[Sequence[str]] = None,
    *,
    graph_client: Optional[GraphClient] = None,
    ssh_transport: Optional[SshTransport] = None,
    token_prompt: Any = None,
) -> int:
    parser = argparse.ArgumentParser(description="Safely transfer Meta read tokens to the GC2 server.")
    parser.add_argument("--host", default="asus-server", help="SSH host alias (default: asus-server).")
    args = parser.parse_args(argv)
    if not isinstance(args.host, str) or not re.fullmatch(r"[A-Za-z0-9._@-]+", args.host) or args.host.startswith("-"):
        _print_error()
        return 2
    if token_prompt is None:
        if not sys.stdin.isatty() or not sys.stderr.isatty():
            _print_error()
            return 2
        token_prompt = lambda: getpass.getpass("Meta long-lived user token (hidden): ")
    try:
        user_token = token_prompt()
        if not isinstance(user_token, str) or not user_token.strip():
            raise SafeUpdateError("user token missing")
        accounts = (graph_client or GraphApiClient()).get_accounts(user_token)
        updates = resolve_meta_tokens(accounts, user_token)
        final_states = (ssh_transport or OpenSshTransport()).update_tokens(args.host, updates)
    except Exception:
        _print_error()
        return 1

    for name in TOKEN_VARIABLES:
        print(name, "DA_DAT")
    for row in final_states:
        print(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
