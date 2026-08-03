from __future__ import annotations


class M04AutomationBridge:
    def request_approval(self, package: dict) -> dict:
        return {"approval_request_id": f"approval-{package['id']}", "status": "pending", "package": package}
