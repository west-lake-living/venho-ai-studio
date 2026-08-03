from __future__ import annotations


class MakeGatewayAdapter:
    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled

    def send(self, command: dict) -> dict:
        if not self.enabled:
            return {"status": "DISABLED", "command_id": command.get("publication_id"), "published": False}
        return {
            "status": "GATEWAY_ACCEPTED",
            "command_id": command.get("publication_id"),
            "published": False,
            "message": "accepted by Make adapter; awaiting callback or reconciliation",
        }
