from __future__ import annotations


class ZaloOAAdapter:
    """Zalo OA channel adapter. Flag off by default (IN-D5) -- ships after
    Phase 4.5 once a dedicated Zalo OA app/quota exists; MVP scope is FB+IG
    only."""

    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled

    def send(self, command: dict) -> dict:
        if not self.enabled:
            return {"status": "DISABLED", "command_id": command.get("publication_id"), "published": False}
        return {
            "status": "GATEWAY_ACCEPTED",
            "command_id": command.get("publication_id"),
            "published": False,
            "message": "accepted by Zalo OA adapter; awaiting callback or reconciliation",
        }
