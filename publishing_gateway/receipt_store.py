from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, Optional, Set

from publishing_gateway.schemas.delivery_receipt import DeliveryReceipt


class ReceiptStore:
    def __init__(self, project: str, data_root: Path = Path("data/projects")) -> None:
        self.project = project
        self.path = data_root / project / "publishing" / "receipt_store.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Dict[str, object]:
        if not self.path.exists():
            return {"receipts": []}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save_receipt(self, receipt: DeliveryReceipt) -> None:
        data = self.load()
        receipts = [item for item in data.get("receipts", []) if item.get("package_id") != receipt.package_id]
        receipts.append(receipt.model_dump(mode="json"))
        data["receipts"] = receipts
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def find_by_package_id(self, package_id: str) -> Optional[Dict[str, object]]:
        for receipt in self.load().get("receipts", []):
            if receipt.get("package_id") == package_id:
                return receipt
        return None

    def successful_platforms(self, idempotency_key: str, platforms: Iterable[str]) -> Set[str]:
        requested = set(platforms)
        successful: Set[str] = set()
        for receipt in self.load().get("receipts", []):
            if receipt.get("idempotency_key") != idempotency_key:
                continue
            for platform, result in receipt.get("platform_results", {}).items():
                if platform in requested and result.get("success") is True:
                    successful.add(platform)
        return successful
