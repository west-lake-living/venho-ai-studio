from __future__ import annotations

import uuid
from typing import Any

from fastapi.responses import JSONResponse


MAX_JSON_BODY_BYTES = 64 * 1024


class RequestMiddleware:
    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        correlation_id = str(uuid.uuid4())
        scope.setdefault("state", {})["correlation_id"] = correlation_id
        path = str(scope.get("path", ""))
        is_private_api = path.startswith(("/api/", "/internal/"))

        async def send_with_metadata(message: dict[str, Any]) -> None:
            if message.get("type") == "http.response.start":
                headers = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() not in {b"x-correlation-id", b"cache-control"}
                ]
                headers.append((b"x-correlation-id", correlation_id.encode("ascii")))
                if is_private_api:
                    headers.append((b"cache-control", b"no-store"))
                message = {**message, "headers": headers}
            await send(message)

        if is_private_api and _is_json_request(scope):
            content_length = _header(scope, b"content-length")
            if content_length:
                try:
                    if int(content_length) > MAX_JSON_BODY_BYTES:
                        await _send_too_large(scope, receive, send_with_metadata, correlation_id)
                        return
                except ValueError:
                    pass

            chunks: list[bytes] = []
            size = 0
            while True:
                message = await receive()
                if message.get("type") != "http.request":
                    await send_with_metadata(message)
                    return
                chunk = message.get("body", b"")
                size += len(chunk)
                if size > MAX_JSON_BODY_BYTES:
                    await _send_too_large(scope, receive, send_with_metadata, correlation_id)
                    return
                chunks.append(chunk)
                if not message.get("more_body", False):
                    break

            body = b"".join(chunks)
            sent = False

            async def replay_receive() -> dict[str, Any]:
                nonlocal sent
                if not sent:
                    sent = True
                    return {"type": "http.request", "body": body, "more_body": False}
                return {"type": "http.disconnect"}

            await self.app(scope, replay_receive, send_with_metadata)
            return

        await self.app(scope, receive, send_with_metadata)


async def _send_too_large(scope: dict[str, Any], receive: Any, send: Any, correlation_id: str) -> None:
    response = JSONResponse(
        status_code=413,
        content={
            "error": {
                "code": "ERR_GC2_PAYLOAD_TOO_LARGE",
                "message": "Tệp quá lớn.",
                "retryable": False,
                "correlation_id": correlation_id,
                "details": {},
            }
        },
    )
    await response(scope, receive, send)


def _is_json_request(scope: dict[str, Any]) -> bool:
    content_type = _header(scope, b"content-type") or ""
    return content_type.split(";", 1)[0].strip().casefold() in {
        "application/json",
        "application/merge-patch+json",
    }


def _header(scope: dict[str, Any], name: bytes) -> str | None:
    for key, value in scope.get("headers", []):
        if key.lower() == name:
            return value.decode("latin-1")
    return None
