from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from enum import Enum
from typing import Any, Mapping, Optional, Protocol, Sequence


class MetaErrorKind(str, Enum):
    AUTH = "AUTH"
    PERMISSION = "PERMISSION"
    NOT_FOUND = "NOT_FOUND"
    RATE_LIMIT = "RATE_LIMIT"
    TRANSIENT = "TRANSIENT"


class MetaGraphError(RuntimeError):
    """Provider error without response text, request URL, or credentials."""

    def __init__(self, kind: Optional[MetaErrorKind], status: Optional[int]) -> None:
        self.kind = kind
        self.status = status
        label = kind.value if kind is not None else "UNCLASSIFIED"
        status_text = f", HTTP {status}" if status is not None else ""
        super().__init__(f"Meta Graph request failed ({label}{status_text})")

    def __repr__(self) -> str:
        label = self.kind.value if self.kind is not None else "UNCLASSIFIED"
        return f"MetaGraphError(kind={label!r}, status={self.status!r})"


class GraphResponse(Protocol):
    status: int
    body: bytes


class GraphTransport(Protocol):
    def get(self, url: str, *, headers: Mapping[str, str], timeout: float) -> GraphResponse:
        """Perform one HTTP GET and return its status and raw body."""


class _UrllibResponse:
    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self.body = body


class UrllibGetTransport:
    """Stdlib GET transport; tests should inject a fake transport."""

    def get(self, url: str, *, headers: Mapping[str, str], timeout: float) -> GraphResponse:
        request = urllib.request.Request(url, headers=dict(headers), method="GET")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return _UrllibResponse(response.status, response.read())
        except urllib.error.HTTPError as exc:
            return _UrllibResponse(exc.code, exc.read())


def _http_error_kind(status: int) -> Optional[MetaErrorKind]:
    if status == 401:
        return MetaErrorKind.AUTH
    if status == 403:
        return MetaErrorKind.PERMISSION
    if status == 404:
        return MetaErrorKind.NOT_FOUND
    if status == 429:
        return MetaErrorKind.RATE_LIMIT
    if status in (408, 425) or status >= 500:
        return MetaErrorKind.TRANSIENT
    # Other 4xx statuses need the P0-T04 probe before assigning a business class.
    return None


def _fields_value(fields: Sequence[str]) -> str:
    values = [str(field).strip() for field in fields]
    if not values or any(not value for value in values):
        raise ValueError("fields must be supplied from verified configuration")
    return ",".join(values)


class ReadOnlyGraphClient:
    """Read-only Graph client with an explicit API version and injected transport."""

    def __init__(
        self,
        *,
        api_version: str,
        access_token: str,
        collection_edge: str,
        transport: Optional[GraphTransport] = None,
        base_url: str = "https://graph.facebook.com",
        timeout: float = 10.0,
    ) -> None:
        version = api_version.strip()
        if not version or version.lower() == "latest" or version == "REQUIRED_FROM_P0":
            raise ValueError("a pinned Meta Graph API version is required")
        token = access_token.strip()
        if not token or token == "REQUIRED_FROM_P0":
            raise ValueError("a Meta read token is required")
        edge = collection_edge.strip().strip("/")
        if not edge or "/" in edge or "?" in edge or "#" in edge:
            raise ValueError("collection_edge must be one configured path segment")
        parsed_base = urllib.parse.urlsplit(base_url)
        if parsed_base.scheme != "https" or not parsed_base.netloc or parsed_base.query or parsed_base.fragment:
            raise ValueError("base_url must be an HTTPS origin")
        if timeout <= 0:
            raise ValueError("timeout must be positive")

        self._api_version = version
        self._access_token = token
        self._collection_edge = edge
        self._transport = transport or UrllibGetTransport()
        self._base_url = f"{parsed_base.scheme}://{parsed_base.netloc}"
        self._timeout = timeout

    def __repr__(self) -> str:
        return (
            "ReadOnlyGraphClient("
            f"api_version={self._api_version!r}, collection_edge={self._collection_edge!r}, "
            "access_token=<redacted>)"
        )

    def get_object(self, object_id: str, fields: Sequence[str]) -> dict[str, Any]:
        path = self._object_path(object_id)
        return self._get_json(path, {"fields": _fields_value(fields)})

    def list_recent_posts(
        self,
        account_id: str,
        since_ms: int,
        until_ms: int,
        fields: Sequence[str],
        max_pages: int,
    ) -> list[dict[str, Any]]:
        if since_ms < 0 or until_ms < since_ms:
            raise ValueError("invalid time window")
        if max_pages < 1:
            raise ValueError("max_pages must be at least one")
        path = f"{self._object_path(account_id)}/{urllib.parse.quote(self._collection_edge, safe='')}"
        query: Optional[dict[str, str]] = {
            "fields": _fields_value(fields),
            "since": str(since_ms // 1000),
            "until": str(until_ms // 1000),
        }
        items: list[dict[str, Any]] = []
        for _ in range(max_pages):
            payload = self._get_json(path, query)
            query = None
            data = payload.get("data")
            if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
                raise MetaGraphError(None, 200)
            items.extend(data)
            paging = payload.get("paging")
            next_url = paging.get("next") if isinstance(paging, dict) else None
            if not next_url:
                break
            path, query = self._validated_next_url(str(next_url))
        return items

    def get_insights(
        self,
        object_id: str,
        metrics: Sequence[str],
        period: Optional[str] = None,
    ) -> dict[str, Any]:
        path = f"{self._object_path(object_id)}/insights"
        params = {"metric": _fields_value(metrics)}
        if period is not None:
            value = period.strip()
            if not value:
                raise ValueError("period must be omitted or supplied from verified configuration")
            params["period"] = value
        return self._get_json(path, params)

    def _object_path(self, object_id: str) -> str:
        value = object_id.strip()
        if not value:
            raise ValueError("object_id is required")
        return f"/{urllib.parse.quote(self._api_version, safe='')}/{urllib.parse.quote(value, safe='')}"

    def _get_json(self, path: str, params: Optional[Mapping[str, str]]) -> dict[str, Any]:
        url = self._absolute_url(path, params)
        try:
            response = self._transport.get(
                url,
                headers={"Authorization": f"Bearer {self._access_token}", "Accept": "application/json"},
                timeout=self._timeout,
            )
        except Exception:
            # Do not chain provider/transport exceptions: their text may contain credentials.
            raise MetaGraphError(MetaErrorKind.TRANSIENT, None) from None
        if response.status < 200 or response.status >= 300:
            raise MetaGraphError(_http_error_kind(response.status), response.status)
        try:
            payload = json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise MetaGraphError(None, response.status) from None
        if not isinstance(payload, dict):
            raise MetaGraphError(None, response.status)
        return payload

    def _absolute_url(self, path: str, params: Optional[Mapping[str, str]]) -> str:
        if not path.startswith("/"):
            raise ValueError("Graph path must be absolute")
        url = f"{self._base_url}{path}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        return url

    def _validated_next_url(self, next_url: str) -> tuple[str, dict[str, str]]:
        candidate = urllib.parse.urlsplit(next_url)
        base = urllib.parse.urlsplit(self._base_url)
        version_prefix = f"/{urllib.parse.quote(self._api_version, safe='')}/"
        if (
            candidate.scheme != "https"
            or candidate.netloc != base.netloc
            or not candidate.path.startswith(version_prefix)
            or candidate.fragment
        ):
            raise MetaGraphError(MetaErrorKind.TRANSIENT, None)
        query_items = urllib.parse.parse_qsl(candidate.query, keep_blank_values=True)
        safe_query = {
            key: value
            for key, value in query_items
            if key.lower() not in {"access_token", "token", "appsecret_proof"}
        }
        return candidate.path, safe_query
