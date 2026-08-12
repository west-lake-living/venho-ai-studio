from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Mapping


class WorkflowRegistry:
    """Versioned, hash-addressed ComfyUI workflow registry."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def load(self, version: str) -> Dict[str, Any]:
        path = self.root / f"{version}_api.json"
        if not path.is_file():
            raise FileNotFoundError(f"Workflow version not found: {version}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Workflow API document must be a JSON object")
        return payload

    def descriptor(self, version: str) -> Dict[str, str]:
        path = self.root / f"{version}_api.json"
        payload = self.load(version)
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return {"version": version, "path": str(path), "sha256": hashlib.sha256(canonical).hexdigest()}

    @staticmethod
    def validate_metadata(metadata: Mapping[str, Any], *, version: str) -> None:
        if metadata.get("workflow_version") != version:
            raise ValueError("Workflow version mismatch in reproducibility metadata")
        if not metadata.get("workflow_sha256"):
            raise ValueError("workflow_sha256 is required for production reproducibility")
