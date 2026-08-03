from __future__ import annotations


class M07PublishingBridge:
    def dispatch(self, command: dict) -> dict:
        return {"publication_id": command["publication_id"], "status": "GATEWAY_ACCEPTED", "idempotency_key": command["idempotency_key"]}
