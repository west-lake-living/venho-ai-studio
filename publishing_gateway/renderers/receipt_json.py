from __future__ import annotations

import json

from publishing_gateway.schemas.delivery_receipt import DeliveryReceipt


def render_receipt_json(receipt: DeliveryReceipt) -> str:
    return json.dumps(receipt.model_dump(mode="json"), ensure_ascii=False, indent=2)
