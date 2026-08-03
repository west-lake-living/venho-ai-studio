from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


class RunStore:
    def __init__(self, project: str = "venho_hotel", data_root: Path = Path("data/projects")) -> None:
        self.root = data_root / project / "growth" / "artifacts"

    def create_run(self, content_package_id: str, run_id: str, image_bytes: bytes, manifest: dict) -> Path:
        folder = self.root / content_package_id / "images" / run_id
        if folder.exists():
            raise FileExistsError(f"Image run already exists: {run_id}")
        folder.mkdir(parents=True)
        artifact_name = manifest.get("artifact_name") or "generated.png"
        artifact_path = folder / artifact_name
        if artifact_path.exists():
            raise FileExistsError(f"Image artifact already exists: {artifact_name}")
        artifact_path.write_bytes(image_bytes)
        payload = {
            **manifest,
            "artifacts": [{"path": artifact_name, "sha256": hashlib.sha256(image_bytes).hexdigest(), "bytes": len(image_bytes)}],
            "created_at": manifest.get("created_at") or datetime.now(timezone.utc).isoformat(),
        }
        (folder / "manifest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return folder

    def list_runs(self, content_package_id: str) -> list[dict]:
        root = self.root / content_package_id / "images"
        if not root.exists():
            return []
        manifests = []
        for manifest_path in sorted(root.glob("*/manifest.json")):
            manifests.append(json.loads(manifest_path.read_text(encoding="utf-8")))
        return manifests
