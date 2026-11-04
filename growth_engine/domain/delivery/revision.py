from __future__ import annotations

import json
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass

from growth_engine.domain.delivery.canonical_payload import build_publish_payload


def normalize_caption(caption: str) -> str:
    """Normalize caption text once, when an immutable revision is created."""
    if not isinstance(caption, str):
        raise TypeError("caption must be a string")
    normalized = unicodedata.normalize("NFC", caption)
    return normalized.replace("\r\n", "\n").replace("\r", "\n")


@dataclass(frozen=True)
class DeliveryRevision:
    payload_json: str
    payload_hash: str

    @classmethod
    def create(cls, payload_fields: Mapping[str, object]) -> DeliveryRevision:
        fields = dict(payload_fields)
        caption = fields.get("caption")
        if not isinstance(caption, str):
            raise ValueError("caption must be a string")
        fields["caption"] = normalize_caption(caption)
        _payload, canonical_bytes, payload_hash = build_publish_payload(**fields)
        return cls(
            payload_json=canonical_bytes.decode("utf-8"),
            payload_hash=payload_hash,
        )

    @property
    def canonical_bytes(self) -> bytes:
        return self.payload_json.encode("utf-8")

    @property
    def payload(self) -> dict[str, object]:
        return json.loads(self.payload_json)
