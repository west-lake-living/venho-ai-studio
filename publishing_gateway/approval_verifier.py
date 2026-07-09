from __future__ import annotations

import hmac
from datetime import timedelta
from hashlib import sha256
from typing import Callable, Optional

from publishing_gateway.exceptions import ERR_APPROVAL_EXPIRED, ERR_APPROVAL_INVALID, ERR_APPROVAL_REQUIRED, PublishingGatewayError
from publishing_gateway.schemas.publishing_request import PublishingRequest
from publishing_gateway.utils.time_utils import parse_utc, utc_now


def build_approval_signature(secret: str, package_id: str, approved_at: str) -> str:
    message = f"{package_id}:{approved_at}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, sha256).hexdigest()


def verify_approval(
    request: PublishingRequest,
    secret: str,
    ttl_minutes: int = 120,
    now_fn: Optional[Callable[[], object]] = None,
) -> bool:
    if request.package_status != "approved":
        raise PublishingGatewayError("package_status must be approved", ERR_APPROVAL_REQUIRED)
    if not request.approval or not request.approval.approval_signature:
        raise PublishingGatewayError("approval signature is required", ERR_APPROVAL_INVALID)

    expected = build_approval_signature(secret, request.package_id, request.approval.approved_at)
    if not hmac.compare_digest(expected, request.approval.approval_signature):
        raise PublishingGatewayError("approval signature mismatch", ERR_APPROVAL_INVALID)

    now = now_fn() if now_fn else utc_now()
    # Fix #7: datetime.fromisoformat() raises ValueError (not PublishingGatewayError) on
    # malformed strings; wrap it so the error carries a stable error_code for callers.
    try:
        approved_at = parse_utc(request.approval.approved_at)
    except ValueError as exc:
        raise PublishingGatewayError(f"approved_at is not a valid UTC datetime: {exc}", ERR_APPROVAL_INVALID) from exc
    if now - approved_at > timedelta(minutes=ttl_minutes):
        raise PublishingGatewayError("approval has expired", ERR_APPROVAL_EXPIRED)
    return True
