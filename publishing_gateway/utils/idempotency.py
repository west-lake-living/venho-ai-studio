from __future__ import annotations

import hashlib
import json
from typing import Any, Dict

from publishing_gateway.schemas.publishing_request import PublishingRequest


def canonical_request_payload(request: PublishingRequest) -> Dict[str, Any]:
    payload = request.model_dump(mode="json")
    # Fix #2: exclude time-variant approval fields (approved_at, approval_signature change
    # on every re-approval). Including them would produce a new hash on re-approval and
    # bypass successful_platforms() dedup, causing duplicate publishes.
    # Also exclude package_status (may change without content changing).
    payload.pop("idempotency_key", None)
    payload.pop("approval", None)
    payload.pop("package_status", None)
    return payload


def generate_idempotency_key(request: PublishingRequest) -> str:
    encoded = json.dumps(canonical_request_payload(request), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def ensure_idempotency_key(request: PublishingRequest) -> PublishingRequest:
    if request.idempotency_key:
        return request
    return request.model_copy(update={"idempotency_key": generate_idempotency_key(request)})
