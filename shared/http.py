from __future__ import annotations

import json as json_lib
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class HttpError(RuntimeError):
    def __init__(self, status: int, body: str) -> None:
        super().__init__(f"HTTP {status}: {body}")
        self.status = status
        self.body = body


def urllib_post(
    url: str,
    *,
    json: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """Stdlib-only POST helper -- default real transport for provider adapters.

    Kept dependency-free on purpose (no requests/httpx) since this project has
    no HTTP library today. Adapters accept an injected transport so tests
    never hit the network.
    """
    body = json_lib.dumps(json or {}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json_lib.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise HttpError(exc.code, exc.read().decode("utf-8")) from exc


def urllib_post_form(
    url: str,
    *,
    data: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """Stdlib-only x-www-form-urlencoded POST helper (some providers, e.g. Zalo OAuth, reject JSON bodies)."""
    body = urllib.parse.urlencode(data or {}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded", **(headers or {})},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json_lib.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise HttpError(exc.code, exc.read().decode("utf-8")) from exc


def urllib_get(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 10.0,
) -> dict[str, Any]:
    if params:
        query = urllib.parse.urlencode(params)
        url = f"{url}?{query}"
    request = urllib.request.Request(url, headers=headers or {}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json_lib.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise HttpError(exc.code, exc.read().decode("utf-8")) from exc
