from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response

from growth_engine.domain.kernel.errors import DomainError, ErrorCode

router = APIRouter(tags=["media"])
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_KEY_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_COMMAND_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
_MEDIA_TTL_GRACE_MS = 30 * 60 * 1000
_MAX_VARIANT_BYTES = 5 * 1024 * 1024


@router.get("/media/publish/{sha256}.jpg", response_class=Response, include_in_schema=False)
def publish_media(sha256: str, request: Request, t: str = Query(default="")) -> Response:
    now_ms = _now_ms(request)
    claims = _verify_token(
        t,
        sha256,
        request.app.state.container.settings.capability_keys,
        now_ms=now_ms,
    )
    if claims is None:
        raise _invalid_capability()
    command_id, expires_at_ms = claims

    container = request.app.state.container
    with container.uow_factory().read_only() as tx:
        row = tx.connection.execute(
            """SELECT oc.state AS command_state, oc.expires_at, oc.revision_id AS command_revision_id,
                      oc.payload_hash AS command_payload_hash,
                      d.active, d.state AS delivery_state, d.current_revision_id,
                      d.active_approval_id, r.id AS revision_id, r.variant_id, r.qc_report_id,
                      r.payload_hash AS revision_payload_hash,
                      a.decision AS approval_decision, a.revision_id AS approval_revision_id,
                      a.payload_hash AS approval_payload_hash,
                      v.sha256 AS variant_sha256, v.object_key, v.mime, v.byte_size,
                      v.qc_status, q.decision AS qc_decision, q.variant_id AS qc_variant_id
               FROM outbox_commands oc
               JOIN deliveries d ON d.id=oc.delivery_id
               JOIN delivery_revisions r ON r.id=oc.revision_id AND r.delivery_id=d.id
               JOIN approval_decisions a ON a.id=d.active_approval_id
               JOIN media_variants v ON v.id=r.variant_id
               JOIN qc_reports q ON q.id=r.qc_report_id
               WHERE oc.id=?""",
            (command_id,),
        ).fetchone()

    if row is None or not _command_still_references_variant(row, sha256, expires_at_ms, now_ms):
        raise _invalid_capability()

    expected_key = f"variants/{sha256[:2]}/{sha256}.jpg"
    if row["object_key"] != expected_key or row["mime"] != "image/jpeg":
        raise _invalid_capability()
    image_path = _safe_media_path(container.settings.media_root, expected_key)
    if image_path is None:
        raise _invalid_capability()
    try:
        image_bytes = image_path.read_bytes()
    except OSError:
        raise _invalid_capability()
    if (
        not image_bytes
        or len(image_bytes) > _MAX_VARIANT_BYTES
        or len(image_bytes) != row["byte_size"]
        or not hmac.compare_digest(hashlib.sha256(image_bytes).hexdigest(), sha256)
    ):
        raise _invalid_capability()
    return Response(
        content=image_bytes,
        media_type="image/jpeg",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.get("/media/publish/{invalid_path:path}", include_in_schema=False)
def reject_invalid_media_path(invalid_path: str) -> None:
    raise _invalid_capability()


def _command_still_references_variant(row: Any, sha256: str, exp_ms: int, now_ms: int) -> bool:
    command_expiry_ms = int(row["expires_at"])
    maximum_expiry_ms = command_expiry_ms + _MEDIA_TTL_GRACE_MS
    return all(
        (
            row["command_state"] in {"DELIVERING", "ACKED", "AUTHORIZED"},
            row["delivery_state"] not in {"BLOCKED", "FAILED_FINAL", "EXPIRED", "CANCELLED", "SUPERSEDED"},
            bool(row["active"]),
            row["revision_id"] == row["command_revision_id"] == row["current_revision_id"],
            row["revision_payload_hash"] == row["command_payload_hash"] == row["approval_payload_hash"],
            row["approval_revision_id"] == row["revision_id"],
            row["approval_decision"] == "APPROVE",
            row["variant_sha256"] == sha256,
            row["qc_variant_id"] == row["variant_id"],
            row["qc_decision"] == "PASS",
            row["qc_status"] == "PASS",
            now_ms <= exp_ms <= maximum_expiry_ms,
            now_ms <= maximum_expiry_ms,
        )
    )


def _verify_token(token: str, sha256: str, key_config: str, *, now_ms: int) -> tuple[str, int] | None:
    if not isinstance(sha256, str) or not _SHA256.fullmatch(sha256):
        return None
    try:
        version, key_id, command_id, raw_expiry, signature = token.split(".")
        if version != "v1" or not _KEY_ID.fullmatch(key_id) or not _COMMAND_ID.fullmatch(command_id):
            return None
        expiry_ms = int(raw_expiry)
        if str(expiry_ms) != raw_expiry or expiry_ms < now_ms:
            return None
        key = _key_for_id(key_config, key_id)
        if key is None:
            return None
        expected = hmac.new(
            key,
            f"{sha256}\n{command_id}\n{expiry_ms}".encode("utf-8"),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(expected, _decode(signature)):
            return None
        return command_id, expiry_ms
    except (TypeError, ValueError):
        return None


def _key_for_id(key_config: str, key_id: str) -> bytes | None:
    for entry in key_config.replace("\n", ",").replace(";", ",").split(","):
        current_id, separator, encoded = entry.strip().partition(":")
        if not separator or current_id != key_id or not encoded.strip():
            continue
        try:
            key = _decode(encoded.strip())
        except ValueError:
            return None
        return key if len(key) >= 32 else None
    return None


def _decode(value: str) -> bytes:
    if not value or any(character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-=" for character in value):
        raise ValueError("invalid base64url value")
    unpadded = value.rstrip("=")
    padded = unpadded + "=" * (-len(unpadded) % 4)
    return base64.b64decode(padded, altchars=b"-_", validate=True)


def _safe_media_path(media_root: str, object_key: str) -> Path | None:
    parts = object_key.split("/")
    if any(part in {"", ".", ".."} for part in parts) or "\\" in object_key:
        return None
    root = Path(media_root).expanduser().resolve()
    path = (root / Path(*parts)).resolve()
    try:
        if os.path.commonpath((str(root), str(path))) != str(root):
            return None
    except ValueError:
        return None
    return path


def _now_ms(request: Request) -> int:
    clock = getattr(request.app.state, "media_clock", None)
    if clock is not None:
        return int(clock.now_ms())
    return time.time_ns() // 1_000_000


def _invalid_capability() -> DomainError:
    return DomainError(ErrorCode.CAPABILITY_INVALID, "Ảnh không khả dụng hoặc liên kết đã hết hạn.")
