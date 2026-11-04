from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json_bytes(value: object) -> bytes:
    _reject_float_or_non_string_key(value)
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("value is not valid canonical JSON") from exc
    return encoded.encode("utf-8")


def _reject_float_or_non_string_key(value: object) -> None:
    if isinstance(value, float):
        raise ValueError("floating point values are not allowed in canonical JSON")
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if not isinstance(key, str):
                raise ValueError("canonical JSON object keys must be strings")
            _reject_float_or_non_string_key(nested)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested in value:
            _reject_float_or_non_string_key(nested)
